#!/usr/bin/env python3
"""Small Pocket TTS HTTP worker for TeamManager.

The default fake mode is dependency-free and exists for Go tests, local smokes,
and managed-sidecar lifecycle work. Real mode is intentionally local-only: it
requires an installed pocket_tts package plus explicit local model and voice
paths, and it sets offline Hugging Face environment defaults before loading.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import struct
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Iterator


# Keep test and smoke runs from writing bytecode into the staged source tree.
sys.dont_write_bytecode = True


DEFAULT_MODEL_DIR = ""
DEFAULT_VOICE_DIR = ""
DEFAULT_SAMPLE_RATE = 24000
WORKER_VERSION = "0.3.0"
WORKER_CAPABILITIES = (
    "health-v1",
    "speech-v1",
    "speech-stream-v1",
    "voice-clone-v1",
    "voice-state-synthesis-v1",
)
STREAM_PROTOCOL_VERSION = "1"
STREAM_CONTENT_TYPE = "application/x-teammanager-pcm-stream"
STREAM_FRAME_AUDIO = 1
STREAM_FRAME_FINAL = 2
STREAM_FRAME_ERROR = 3
STREAM_FRAME_HEADER = struct.Struct(">BII")
MAX_STREAM_CHUNK_BYTES = 1024 * 1024
DEFAULT_MAX_BODY_BYTES = 8192
DEFAULT_MAX_TEXT_CHARS = 600
DEFAULT_REQUEST_TIMEOUT_MS = 15000
DEFAULT_MAX_QUEUE = 1
MAX_AUDIO_BYTES = 64 * 1024 * 1024
MAX_REFERENCE_BYTES = 64 * 1024 * 1024
MAX_STATE_BYTES = 256 * 1024 * 1024
CLONE_PATH = "/v1/voices/clone"
STATE_SYNTH_PATH = "/v1/audio/speech/state"
CLONE_LANGUAGES = ("english",)
SUPPORTED_LANGUAGES = frozenset((
        "english",
        "english_2026-01",
        "english_2026-04",
        "french_24l",
        "german",
        "german_24l",
        "portuguese",
        "portuguese_24l",
        "italian",
        "italian_24l",
        "spanish",
        "spanish_24l",
))


@dataclass(frozen=True)
class WorkerConfig:
    mode: str
    host: str
    port: int
    model_dir: str
    voice_dir: str
    default_voice: str
    language: str
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS
    request_timeout_ms: int = DEFAULT_REQUEST_TIMEOUT_MS
    max_queue: int = DEFAULT_MAX_QUEUE
    fake_delay_ms: int = 0
    cpu_threads: int = 2
    state_compatibility_manifest: str = ""


COMPATIBILITY_FIELDS = (
    "schema", "fingerprint_schema", "provider_kind", "pocket_package_version",
    "python_version", "python_abi", "torch_version", "torch_build",
    "worker_state_contract_version", "model_id", "model_revision", "model_sha256",
    "model_config_sha256", "clone_languages", "state_export_api", "state_format",
)


def _reject_duplicate_json_names(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON member")
        result[name] = value
    return result


def load_activated_state_compatibility(path: str) -> dict[str, Any] | None:
    """Loads only the desktop-activated closed object from installed-bundle.json."""
    if not path:
        return None
    source = Path(path)
    if not source.is_file() or source.stat().st_size < 2 or source.stat().st_size > 64 * 1024:
        raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    try:
        installed = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_json_names)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise CloneWeightsUnavailableError("verified clone compatibility is unavailable") from error
    compatibility = installed.get("state_compatibility") if isinstance(installed, dict) else None
    if not isinstance(compatibility, dict) or tuple(compatibility) != COMPATIBILITY_FIELDS:
        raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    if compatibility["schema"] != "pocket-state-manifest-v1" or compatibility["fingerprint_schema"] != "pocket-state-compat-v1" or compatibility["provider_kind"] != "pocket_tts_managed":
        raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    identifier = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/+:-]{0,127}\Z")
    digest = re.compile(r"[0-9a-f]{64}\Z")
    for name in ("pocket_package_version", "python_version", "python_abi", "torch_version", "torch_build", "worker_state_contract_version", "model_id", "model_revision", "state_export_api", "state_format"):
        if not isinstance(compatibility[name], str) or not identifier.fullmatch(compatibility[name]):
            raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    for name in ("model_sha256", "model_config_sha256"):
        if not isinstance(compatibility[name], str) or not digest.fullmatch(compatibility[name]):
            raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    rows = compatibility["clone_languages"]
    if not isinstance(rows, list) or len(rows) != len(CLONE_LANGUAGES):
        raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    for expected, row in zip(CLONE_LANGUAGES, rows, strict=True):
        if not isinstance(row, dict) or tuple(row) != ("language", "cloning_weights_sha256") or row["language"] != expected or not isinstance(row["cloning_weights_sha256"], str) or not digest.fullmatch(row["cloning_weights_sha256"]):
            raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    return compatibility


def state_compatibility_fingerprint(compatibility: dict[str, Any], language: str) -> tuple[str, str]:
    language = validate_clone_language(language)
    weights = next((row["cloning_weights_sha256"] for row in compatibility["clone_languages"] if row["language"] == language), "")
    if not weights:
        raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
    preimage = (
        '{"schema":"pocket-state-compat-v1","provider_kind":"' + compatibility["provider_kind"] +
        '","pocket_package_version":"' + compatibility["pocket_package_version"] +
        '","python_version":"' + compatibility["python_version"] + '","python_abi":"' + compatibility["python_abi"] +
        '","torch_version":"' + compatibility["torch_version"] + '","torch_build":"' + compatibility["torch_build"] +
        '","worker_state_contract_version":"' + compatibility["worker_state_contract_version"] +
        '","model_id":"' + compatibility["model_id"] + '","model_revision":"' + compatibility["model_revision"] +
        '","model_sha256":"' + compatibility["model_sha256"] + '","model_config_sha256":"' + compatibility["model_config_sha256"] +
        '","cloning_weights_sha256":"' + weights + '","language":"' + language +
        '","state_export_api":"' + compatibility["state_export_api"] + '","state_format":"' + compatibility["state_format"] + '"}'
    )
    return preimage, hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def runtime_matches_activated_compatibility(compatibility: dict[str, Any]) -> bool:
    try:
        pocket_version = importlib.metadata.version("pocket-tts")
        torch_version = importlib.metadata.version("torch")
    except importlib.metadata.PackageNotFoundError:
        return False
    return (
        compatibility["pocket_package_version"] == pocket_version == "2.1.0"
        and compatibility["python_version"] == platform.python_version()
        and compatibility["python_abi"] == f"cp{sys.version_info.major}{sys.version_info.minor}-win_amd64"
        and compatibility["torch_version"] == torch_version == "2.5.1+cpu"
        and compatibility["torch_build"] == "cpu-cp311-win_amd64"
        and compatibility["worker_state_contract_version"] == "pocket-worker-state-v1"
        and compatibility["state_export_api"] == "pocket.export_model_state-v1"
        and compatibility["state_format"] == "safetensors-v1"
        and platform.system() == "Windows"
        and platform.machine().lower() in {"amd64", "x86_64"}
    )


class FakeSynthesizer:
    """Generates a valid short WAV without importing Pocket dependencies."""

    sample_rate = DEFAULT_SAMPLE_RATE

    def health(self) -> dict[str, Any]:
        return {
            "status": "degraded",
            "reason": "fake_mode_transport_only",
            "message": "fake Pocket worker is test-only",
            "mode": "fake",
            "worker_version": WORKER_VERSION,
            "capabilities": list(WORKER_CAPABILITIES),
            "model_loaded": False,
            "model_path_valid": True,
            "voice_path_valid": True,
            "dependency_ready": True,
            "active_language": "english",
            "sample_rate": self.sample_rate,
            "queue_depth": 0,
            "last_error": "fake_mode_transport_only",
            "transport_ready": True,
            "inference_ready": False,
        }

    def synthesize(self, request: dict[str, Any]) -> bytes:
        text = str(request.get("text", "")).strip()
        radio_fx = bool(request.get("radio_fx", False))
        delay_ms = int(request.get("_fake_delay_ms", 0) or 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        duration = min(0.9, max(0.25, 0.018 * len(text)))
        frequency = 330.0 if radio_fx else 220.0
        amplitude = 0.26 if radio_fx else 0.20
        return wav_from_pcm16(sine_pcm16(duration, frequency, amplitude, self.sample_rate), self.sample_rate)

    def synthesize_stream(self, request: dict[str, Any]) -> Iterator[bytes]:
        """Yields deterministic PCM chunks for protocol and playback tests."""
        wav = self.synthesize(request)
        pcm = wav_pcm16(wav)
        chunk_bytes = 960 * 2
        for offset in range(0, len(pcm), chunk_bytes):
            yield pcm[offset : offset + chunk_bytes]


class RealPocketSynthesizer:
    """Loads pocket_tts lazily from explicit local model and voice paths."""

    def __init__(
        self,
        config: WorkerConfig,
        adapter: Any | None = None,
        activated_compatibility: dict[str, Any] | None = None,
    ) -> None:
        self.config = config
        self.adapter = adapter or PocketDependencyAdapter()
        self.model: Any | None = None
        self.voice_states: dict[str, Any] = {}
        self.sample_rate = DEFAULT_SAMPLE_RATE
        self.loaded_language: str | None = None
        self.loaded_parameters: tuple[float, int, float] | None = None
        self.inference_verified = False
        self._load_lock = threading.Lock()
        self._load_error = ""
        self._load_thread: threading.Thread | None = None
        self.activated_compatibility = activated_compatibility

    def clone(self, reference_wav: bytes, language: str) -> tuple[bytes, str]:
        """Derives and exports Pocket state without retaining caller bytes or paths."""
        if self.activated_compatibility is None or not runtime_matches_activated_compatibility(self.activated_compatibility):
            raise CloneWeightsUnavailableError("verified clone compatibility is unavailable")
        language = validate_clone_language(language)
        _, fingerprint = state_compatibility_fingerprint(self.activated_compatibility, language)
        model = self._load_model(language, 0.7, 1, -4.0)
        if getattr(model, "has_voice_cloning", None) is not True:
            raise CloneWeightsUnavailableError("verified Pocket cloning weights are unavailable")

        with tempfile.TemporaryDirectory(prefix="teammanager-pocket-clone-") as temp_dir:
            reference_path = Path(temp_dir) / "reference.wav"
            state_path = Path(temp_dir) / "state.safetensors"
            reference_path.write_bytes(reference_wav)
            state = model.get_state_for_audio_prompt(str(reference_path), truncate=True)
            self.adapter.export_model_state(state, state_path)
            size = state_path.stat().st_size
            if size < 1 or size > MAX_STATE_BYTES:
                raise StateInvalidError("exported state violates the response bound")
            state_bytes = state_path.read_bytes()
            validate_safetensors(state_bytes)
        return state_bytes, fingerprint

    def synthesize_state(
        self,
        state_bytes: bytes,
        state_sha256: str,
        compatibility_fingerprint: str,
        language: str,
        text: str,
    ) -> bytes:
        """Loads caller-supplied persisted state bytes and synthesizes without a catalog fallback."""
        if self.activated_compatibility is None or not runtime_matches_activated_compatibility(self.activated_compatibility):
            raise ConflictError("persisted state is incompatible with the activated worker")
        _, expected_fingerprint = state_compatibility_fingerprint(self.activated_compatibility, language)
        if compatibility_fingerprint != expected_fingerprint:
            raise ConflictError("persisted state is incompatible with the activated worker")
        if hashlib.sha256(state_bytes).hexdigest() != state_sha256:
            raise StateInvalidError("persisted state hash mismatch")
        validate_safetensors(state_bytes)
        language = validate_clone_language(language)
        text = text.strip()
        if not text or len(text) > self.config.max_text_chars:
            raise ValueError("text is required and must be bounded")
        model = self._load_model(language, 0.7, 1, -4.0)
        with tempfile.TemporaryDirectory(prefix="teammanager-pocket-state-") as temp_dir:
            state_path = Path(temp_dir) / "state.safetensors"
            state_path.write_bytes(state_bytes)
            voice_state = self.adapter.import_model_state(state_path, model.device)
            audio = model.generate_audio(voice_state, text)
        sample_rate = int(getattr(model, "sample_rate", self.sample_rate) or self.sample_rate)
        pcm = tensor_like_to_pcm16(audio)
        if not pcm or len(pcm) % 2:
            raise RuntimeError("Pocket state synthesis returned invalid PCM16 audio")
        result = wav_from_pcm16(pcm, sample_rate)
        if len(result) > MAX_AUDIO_BYTES:
            raise RuntimeError("Pocket state synthesis exceeded the response bound")
        self.sample_rate = sample_rate
        self.inference_verified = True
        return result

    def health(self) -> dict[str, Any]:
        voice_dir = Path(self.config.voice_dir)
        try:
            self._resolve_model_config(self.config.language)
            model_path_valid = True
        except (ValueError, DependencyError) as exc:
            return self._health(
                "degraded",
                reason="local_missing_model",
                model_loaded=False,
                model_path_valid=False,
                voice_path_valid=voice_dir.is_dir(),
                dependency_ready=self._dependency_ready(),
                last_error=str(exc),
                inference_ready=False,
            )
        if not voice_dir.is_dir() or not directory_has_voice_files(voice_dir):
            return self._health(
                "degraded",
                reason="local_missing_voice",
                model_loaded=False,
                model_path_valid=model_path_valid,
                voice_path_valid=False,
                dependency_ready=self._dependency_ready(),
                last_error=f"voice_dir has no local WAV or voice state: {voice_dir}",
                inference_ready=False,
            )
        if not self._dependency_ready():
            return self._health(
                "degraded",
                reason="local_missing_dependency",
                model_loaded=False,
                model_path_valid=model_path_valid,
                voice_path_valid=True,
                dependency_ready=False,
                last_error="pocket_tts dependency is unavailable",
                inference_ready=False,
            )
        self._ensure_model_preload()
        if self._load_error:
            return self._health(
                "degraded",
                reason="real_model_preload_failed",
                model_loaded=False,
                model_path_valid=model_path_valid,
                voice_path_valid=True,
                dependency_ready=True,
                last_error=self._load_error,
                inference_ready=False,
            )
        if self.model is None:
            return self._health(
                "starting",
                reason="loading_model",
                model_loaded=False,
                model_path_valid=model_path_valid,
                voice_path_valid=True,
                dependency_ready=True,
                last_error="loading model",
                inference_ready=False,
            )
        if not self.inference_verified:
            return self._health(
                "degraded",
                reason="real_inference_not_verified",
                model_loaded=True,
                model_path_valid=model_path_valid,
                voice_path_valid=True,
                dependency_ready=True,
                last_error="Pocket inputs are present, but no real synthesis has completed in this worker process",
                inference_ready=False,
            )
        return self._health(
            "ready",
            reason="",
            model_loaded=True,
            model_path_valid=model_path_valid,
            voice_path_valid=True,
            dependency_ready=True,
            last_error="",
            inference_ready=True,
        )

    def _dependency_ready(self) -> bool:
        try:
            self.adapter.ensure_available()
            return True
        except Exception:
            return False

    def _health(
        self,
        status: str,
        *,
        reason: str,
        model_loaded: bool,
        model_path_valid: bool,
        voice_path_valid: bool,
        dependency_ready: bool,
        last_error: str,
        inference_ready: bool,
    ) -> dict[str, Any]:
        message = sanitize_error(last_error)
        payload = {
            "status": status,
            "reason": reason,
            "message": message,
            "mode": "real",
            "worker_version": WORKER_VERSION,
            "capabilities": list(WORKER_CAPABILITIES),
            "model_loaded": model_loaded,
            "model_path_valid": model_path_valid,
            "voice_path_valid": voice_path_valid,
            "dependency_ready": dependency_ready,
            "active_language": self.config.language,
            "sample_rate": self.sample_rate,
            "queue_depth": 0,
            "last_error": message,
            "transport_ready": True,
            "inference_ready": inference_ready,
        }
        return payload

    def synthesize(self, request: dict[str, Any]) -> bytes:
        text = str(request.get("text", "")).strip()
        if not text:
            raise ValueError("text is required")
        language = validate_language(str(request.get("language") or self.config.language).strip())
        temperature = finite_float(request.get("temperature", 0.7), "temperature")
        if temperature <= 0:
            raise ValueError("temperature must be greater than zero")
        lsd_decode_steps = int(request.get("lsd_decode_steps", 1) or 0)
        if lsd_decode_steps < 1:
            raise ValueError("lsd_decode_steps must be at least one")
        eos_threshold = finite_float(request.get("eos_threshold", -4.0), "eos_threshold")
        if eos_threshold > 0:
            raise ValueError("eos_threshold must be zero or negative")

        model = self._load_model(language, temperature, lsd_decode_steps, eos_threshold)
        voice_ref = self._resolve_voice_ref(str(request.get("voice_id") or self.config.default_voice).strip())
        voice_state = self._load_voice_state(model, voice_ref)
        audio = model.generate_audio(voice_state, text)
        sample_rate = int(getattr(model, "sample_rate", self.sample_rate) or self.sample_rate)
        pcm = tensor_like_to_pcm16(audio)
        if not pcm or len(pcm) % 2 != 0:
            raise RuntimeError("Pocket synthesis returned empty or invalid PCM16 audio")
        wav = wav_from_pcm16(pcm, sample_rate)
        self.sample_rate = sample_rate
        self.inference_verified = True
        return wav

    def synthesize_stream(self, request: dict[str, Any]) -> Iterator[bytes]:
        """Yields Pocket 2.1 stream chunks without buffering a completed WAV."""
        text, model, voice_state = self._prepare_synthesis(request)
        yield from self._generate_prepared_stream(text, model, voice_state)

    def prepare_stream(self, request: dict[str, Any]) -> tuple[Iterator[bytes], int]:
        """Prepares model and voice once, returning PCM iteration and its exact rate."""
        text, model, voice_state = self._prepare_synthesis(request)
        generate = getattr(model, "generate_audio_stream", None)
        if not callable(generate):
            raise StreamingUnsupportedError("Pocket generate_audio_stream is unavailable")
        sample_rate = int(getattr(model, "sample_rate", self.sample_rate) or self.sample_rate)
        self.sample_rate = sample_rate
        return self._generate_prepared_stream(text, model, voice_state), sample_rate

    def _generate_prepared_stream(self, text: str, model: Any, voice_state: Any) -> Iterator[bytes]:
        generate = getattr(model, "generate_audio_stream", None)
        if not callable(generate):
            raise StreamingUnsupportedError("Pocket generate_audio_stream is unavailable")
        yielded = False
        for audio in generate(voice_state, text):
            pcm = tensor_like_to_pcm16(audio)
            if not pcm or len(pcm) % 2:
                raise RuntimeError("Pocket streaming returned empty or invalid PCM16 audio")
            yielded = True
            yield pcm
        if not yielded:
            raise RuntimeError("Pocket streaming returned no audio")
        self.sample_rate = int(getattr(model, "sample_rate", self.sample_rate) or self.sample_rate)
        self.inference_verified = True

    def _prepare_synthesis(self, request: dict[str, Any]) -> tuple[str, Any, Any]:
        text = str(request.get("text", "")).strip()
        language = validate_language(str(request.get("language") or self.config.language).strip())
        temperature = finite_float(request.get("temperature", 0.7), "temperature")
        lsd_decode_steps = int(request.get("lsd_decode_steps", 1) or 0)
        eos_threshold = finite_float(request.get("eos_threshold", -4.0), "eos_threshold")
        model = self._load_model(language, temperature, lsd_decode_steps, eos_threshold)
        voice_ref = self._resolve_voice_ref(str(request.get("voice_id") or self.config.default_voice).strip())
        return text, model, self._load_voice_state(model, voice_ref)

    def _ensure_model_preload(self) -> None:
        with self._load_lock:
            if self.model is not None:
                return
            if self._load_thread is not None and self._load_thread.is_alive():
                return
            self._load_error = ""
            self._load_thread = threading.Thread(target=self._preload_model, daemon=True)
            self._load_thread.start()

    def _preload_model(self) -> None:
        try:
            self._load_model(self.config.language, 0.7, 1, -4.0)
        except Exception as exc:
            with self._load_lock:
                self._load_error = str(exc)

    def _load_model(self, language: str, temperature: float, lsd_decode_steps: int, eos_threshold: float) -> Any:
        signature = (temperature, lsd_decode_steps, eos_threshold)
        with self._load_lock:
            if self.model is not None:
                if self.loaded_language != language or self.loaded_parameters != signature:
                    raise ConflictError("loaded Pocket model parameters are incompatible with the request")
                return self.model

            config_path = self._resolve_model_config(language)
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            normalized_config_path, cleanup = self._materialize_normalized_model_config(config_path)
            self.adapter.ensure_available()
            tts_model = self.adapter.tts_model_class()
            try:
                model = tts_model.load_model(
                    config=str(normalized_config_path),
                    temp=temperature,
                    lsd_decode_steps=lsd_decode_steps,
                    eos_threshold=eos_threshold,
                )
            finally:
                cleanup()
            self.model = model
            self.loaded_language = language
            self.loaded_parameters = signature
            self.sample_rate = int(getattr(model, "sample_rate", DEFAULT_SAMPLE_RATE) or DEFAULT_SAMPLE_RATE)
            self._load_error = ""
            return model

    def _resolve_model_config(self, language: str) -> Path:
        language = validate_language(language)
        model_root = Path(self.config.model_dir)
        if model_root.is_file() and model_root.suffix.lower() in {".yaml", ".yml"}:
            return model_root.resolve()
        if not model_root.is_dir():
            raise DependencyError(f"Pocket model directory is not configured or missing: {model_root}")
        candidates = (
            model_root / language / "config.yaml",
            model_root / "config.yaml",
            model_root / "model" / language / "config.yaml",
            model_root / "model" / "config.yaml",
            model_root / "models" / language / "config.yaml",
            model_root / "models" / "config.yaml",
        )
        resolved_root = model_root.resolve()
        for candidate in candidates:
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved_root not in resolved.parents:
                raise ValueError("model config resolved outside allowed root")
            return resolved
        raise DependencyError("Pocket model config.yaml is missing from the configured model directory")

    def _materialize_normalized_model_config(self, config_path: Path) -> tuple[Path, Callable[[], None]]:
        config_root = self._allowed_model_root(config_path)
        original_text = config_path.read_text(encoding="utf-8")
        normalized_text = normalize_model_config_paths(original_text, config_path, config_root)
        temp_config = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".yaml",
            prefix="teammanager-pocket-config-",
            dir=str(config_path.parent),
            delete=False,
        )
        try:
            temp_config.write(normalized_text)
            temp_path = Path(temp_config.name)
        finally:
            temp_config.close()

        def cleanup() -> None:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

        return temp_path, cleanup

    def _allowed_model_root(self, config_path: Path) -> Path:
        model_root = Path(self.config.model_dir)
        if model_root.is_file():
            resolved = model_root.resolve()
            return resolved.parent
        if model_root.is_dir():
            return model_root.resolve()
        return config_path.parent.resolve()

    def _load_voice_state(self, model: Any, voice_ref: str) -> Any:
        if voice_ref in self.voice_states:
            return self.voice_states[voice_ref]
        state = model.get_state_for_audio_prompt(voice_ref)
        self.voice_states[voice_ref] = state
        return state

    def _resolve_voice_ref(self, voice_id: str) -> str:
        if not voice_id:
            raise RuntimeError("voice_id is required in real mode")
        voice_dir = Path(self.config.voice_dir)
        if not voice_dir.exists():
            raise DependencyError(f"Pocket voice directory is not configured or missing: {voice_dir}")
        if Path(voice_id).is_absolute():
            raise ValueError("absolute voice_id paths are not allowed")
        if ".." in Path(voice_id).parts:
            raise ValueError("voice_id traversal is not allowed")

        candidates = [
            voice_dir / voice_id,
            voice_dir / f"{voice_id}.wav",
            voice_dir / f"{voice_id}.safetensors",
        ]
        resolved_root = voice_dir.resolve()
        for candidate in candidates:
            if not candidate.exists():
                continue
            resolved = candidate.resolve()
            if resolved_root not in resolved.parents and resolved != resolved_root:
                raise ValueError("voice_id resolved outside allowed root")
            return str(resolved)
        raise ConflictError(f"voice_id {voice_id!r} was not found under configured voice directory")


class BusyError(RuntimeError):
    """Signals queue or concurrency exhaustion."""


class ConflictError(RuntimeError):
    """Signals incompatible request, model, or voice state."""


class TimeoutError(RuntimeError):
    """Signals bounded synthesis timeout."""


class DependencyError(RuntimeError):
    """Signals missing worker dependencies or incomplete local setup."""


class StreamingUnsupportedError(RuntimeError):
    """Signals that the installed Pocket API cannot incrementally generate."""


class CloneWeightsUnavailableError(RuntimeError):
    """Signals that authenticated clone compatibility/weights are unavailable."""


class StateInvalidError(RuntimeError):
    """Signals that Pocket did not export a bounded valid safetensors artifact."""


class PocketDependencyAdapter:
    """Wraps pocket_tts imports so tests can supply a fake dependency surface."""

    def ensure_available(self) -> None:
        __import__("pocket_tts")

    def tts_model_class(self) -> Any:
        from pocket_tts import TTSModel  # type: ignore

        return TTSModel

    def export_model_state(self, state: Any, destination: Path) -> None:
        from pocket_tts import export_model_state  # type: ignore

        export_model_state(state, destination)

    def import_model_state(self, source: Path, device: Any) -> Any:
        from pocket_tts.models.tts_model import _import_model_state  # type: ignore

        return _import_model_state(source, device)


MODEL_CONFIG_PATH_PATTERN = re.compile(r"^(\s*)(weights_path|tokenizer_path)(\s*:\s*)(.+?)(\s*(?:#.*)?)$")


def normalize_model_config_paths(config_text: str, config_path: Path, allowed_root: Path) -> str:
    normalized_lines: list[str] = []
    for line in config_text.splitlines(keepends=True):
        match = MODEL_CONFIG_PATH_PATTERN.match(line.rstrip("\r\n"))
        if not match:
            normalized_lines.append(line)
            continue
        indent, key, separator, raw_value, suffix = match.groups()
        normalized_value = normalize_config_path_value(raw_value.strip(), config_path, allowed_root)
        line_ending = "\n" if line.endswith("\n") else ""
        normalized_lines.append(f"{indent}{key}{separator}{normalized_value}{suffix}{line_ending}")
    return "".join(normalized_lines)


def normalize_config_path_value(raw_value: str, config_path: Path, allowed_root: Path) -> str:
    value, quote = parse_yaml_scalar(raw_value)
    if not value:
        raise ValueError("model config path is empty")
    if value.startswith("hf://"):
        return format_yaml_scalar(value, quote)

    local_path = Path(value)
    if local_path.is_absolute():
        candidate = local_path.resolve()
    else:
        candidate = (config_path.parent / local_path).resolve()
    assert_path_within_root(candidate, allowed_root, "model config path")
    return format_yaml_scalar(str(candidate), quote)


def parse_yaml_scalar(raw_value: str) -> tuple[str, str]:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1], value[0]
    return value, ""


def format_yaml_scalar(value: str, quote: str) -> str:
    if quote == "'":
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    if quote == '"':
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if any(char in value for char in " #:{}[]&,*>!|%@`"):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def assert_path_within_root(candidate: Path, allowed_root: Path, label: str) -> None:
    resolved_root = allowed_root.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_candidate != resolved_root and resolved_root not in resolved_candidate.parents:
        raise ValueError(f"{label} escapes allowed root")


class PocketWorkerServer(ThreadingHTTPServer):
    """Threaded worker server with single-flight synthesis and a bounded queue."""

    def __init__(self, server_address: tuple[str, int], handler: type[BaseHTTPRequestHandler], synthesizer: Any, config: WorkerConfig) -> None:
        super().__init__(server_address, handler)
        self.synthesizer = synthesizer
        self.config = config
        self._synth_lock = threading.Lock()
        self._queue_lock = threading.Lock()
        self._queue_depth = 0

    @property
    def queue_depth(self) -> int:
        with self._queue_lock:
            return self._queue_depth

    def worker_health(self) -> dict[str, Any]:
        payload = dict(self.synthesizer.health())
        payload["queue_depth"] = self.queue_depth
        return payload

    def run_synthesis(self, request: dict[str, Any]) -> bytes:
        acquired = self._synth_lock.acquire(blocking=False)
        if not acquired:
            with self._queue_lock:
                if self._queue_depth >= self.config.max_queue:
                    raise BusyError("worker queue is full")
                self._queue_depth += 1
            deadline = time.monotonic() + (self.config.request_timeout_ms / 1000.0)
            try:
                while time.monotonic() < deadline:
                    if self._synth_lock.acquire(timeout=0.05):
                        acquired = True
                        break
            finally:
                with self._queue_lock:
                    self._queue_depth = max(self._queue_depth - 1, 0)
            if not acquired:
                raise TimeoutError("worker busy timeout")

        payload = dict(request)
        if self.config.fake_delay_ms > 0:
            payload["_fake_delay_ms"] = self.config.fake_delay_ms

        result: list[bytes | Exception] = []

        def _target() -> None:
            try:
                result.append(self.synthesizer.synthesize(payload))
            except Exception as exc:
                result.append(exc)
            finally:
                self._synth_lock.release()

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(self.config.request_timeout_ms / 1000.0)
        if thread.is_alive():
            raise TimeoutError("synthesis timed out")
        if result and isinstance(result[0], Exception):
            raise result[0]
        if not result:
            raise RuntimeError("worker returned no result")
        return result[0]

    def run_clone(self, reference_wav: bytes, language: str) -> tuple[bytes, str]:
        if not self._synth_lock.acquire(blocking=False):
            raise BusyError("worker is busy")
        result: list[tuple[bytes, str] | Exception] = []

        def _target() -> None:
            try:
                clone = getattr(self.synthesizer, "clone", None)
                if not callable(clone):
                    raise CloneWeightsUnavailableError("Pocket clone capability is unavailable")
                result.append(clone(reference_wav, language))
            except Exception as exc:
                result.append(exc)
            finally:
                self._synth_lock.release()

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(self.config.request_timeout_ms / 1000.0)
        if thread.is_alive():
            raise TimeoutError("clone timed out")
        if result and isinstance(result[0], Exception):
            raise result[0]
        if not result:
            raise RuntimeError("worker returned no clone result")
        return result[0]

    def run_state_synthesis(self, state: bytes, state_sha256: str, fingerprint: str, language: str, text: str) -> bytes:
        if not self._synth_lock.acquire(blocking=False):
            raise BusyError("worker is busy")
        result: list[bytes | Exception] = []

        def _target() -> None:
            try:
                synthesize = getattr(self.synthesizer, "synthesize_state", None)
                if not callable(synthesize):
                    raise CloneWeightsUnavailableError("Pocket persisted-state synthesis is unavailable")
                result.append(synthesize(state, state_sha256, fingerprint, language, text))
            except Exception as exc:
                result.append(exc)
            finally:
                self._synth_lock.release()

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(self.config.request_timeout_ms / 1000.0)
        if thread.is_alive():
            raise TimeoutError("state synthesis timed out")
        if result and isinstance(result[0], Exception):
            raise result[0]
        if not result:
            raise RuntimeError("worker returned no state synthesis result")
        return result[0]

    def run_stream(self, request: dict[str, Any]) -> Iterator[bytes]:
        if not self._synth_lock.acquire(blocking=False):
            raise BusyError("worker is busy")
        payload = dict(request)
        if self.config.fake_delay_ms > 0:
            payload["_fake_delay_ms"] = self.config.fake_delay_ms
        try:
            yield from self.synthesizer.synthesize_stream(payload)
        finally:
            self._synth_lock.release()

    def prepare_stream(self, request: dict[str, Any]) -> tuple[Iterator[bytes], int]:
        """Claims single-flight and completes fallible preparation before headers."""
        if not self._synth_lock.acquire(blocking=False):
            raise BusyError("worker is busy")
        payload = dict(request)
        if self.config.fake_delay_ms > 0:
            payload["_fake_delay_ms"] = self.config.fake_delay_ms
        try:
            prepare = getattr(self.synthesizer, "prepare_stream", None)
            if callable(prepare):
                chunks, sample_rate = prepare(payload)
            else:
                chunks = self.synthesizer.synthesize_stream(payload)
                sample_rate = int(self.synthesizer.sample_rate)
        except Exception:
            self._synth_lock.release()
            raise

        def _owned_chunks() -> Iterator[bytes]:
            try:
                yield from chunks
            finally:
                # Pocket exposes no reliable mid-call cancellation. Closing the
                # HTTP stream stops consumption, while this owner retains the
                # synthesis slot until generator cleanup/natural completion.
                self._synth_lock.release()

        return _owned_chunks(), sample_rate


class PocketWorkerHandler(BaseHTTPRequestHandler):
    server_version = f"TeamManagerPocketTTSWorker/{WORKER_VERSION}"

    def log_message(self, format: str, *args: Any) -> None:
        if os.environ.get("POCKET_TTS_WORKER_LOG_REQUESTS") == "1":
            super().log_message(format, *args)

    def do_GET(self) -> None:
        if self.path != "/health":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self._json(HTTPStatus.OK, self.server.worker_health())  # type: ignore[attr-defined]

    def do_POST(self) -> None:
        if self.path == CLONE_PATH:
            self._clone()
            return
        if self.path == STATE_SYNTH_PATH:
            self._state_synthesis()
            return
        if self.path != "/v1/audio/speech":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            request = self._read_json()
            text = str(request.get("text", "")).strip()
            if not text:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "text is required"})
                return
            if len(text) > self.server.config.max_text_chars:  # type: ignore[attr-defined]
                self._json(HTTPStatus.BAD_REQUEST, {"error": "text exceeds configured limit"})
                return
            validate_request(request)
            if request.get("stream", False):
                self._stream(request)
                return
            audio = self.server.run_synthesis(request)  # type: ignore[attr-defined]
            if not audio or len(audio) > MAX_AUDIO_BYTES:
                raise RuntimeError("worker audio result is empty or exceeds the response limit")
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return
        except BusyError as exc:
            self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": sanitize_error(str(exc))})
            return
        except TimeoutError as exc:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": sanitize_error(str(exc))})
            return
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": sanitize_error(str(exc))})
            return
        except ConflictError as exc:
            self._json(HTTPStatus.CONFLICT, {"error": sanitize_error(str(exc))})
            return
        except DependencyError as exc:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": sanitize_error(str(exc))})
            return
        except Exception as exc:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": sanitize_error(f"internal worker failure: {type(exc).__name__}: {exc}")})
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)

    def _clone(self) -> None:
        try:
            reference_wav, language = self._read_clone_reference()
            state, fingerprint = self.server.run_clone(reference_wav, language)  # type: ignore[attr-defined]
            if not state or len(state) > MAX_STATE_BYTES:
                raise StateInvalidError("exported state violates the response bound")
            state_sha256 = hashlib.sha256(state).hexdigest()
        except CloneProtocolError as exc:
            self._json(exc.status, {"error": exc.code})
            return
        except BusyError:
            self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "clone_busy"})
            return
        except TimeoutError:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "clone_timeout"})
            return
        except CloneWeightsUnavailableError:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "clone_weights_unavailable"})
            return
        except StateInvalidError:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "state_invalid"})
            return
        except (ValueError, ConflictError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "clone_failed"})
            return
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "clone_failed"})
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-safetensors")
        self.send_header("Content-Length", str(len(state)))
        self.send_header("X-TeamManager-State-SHA256", state_sha256)
        self.send_header("X-TeamManager-Compatibility-Fingerprint", fingerprint)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(state)

    def _state_synthesis(self) -> None:
        try:
            state, state_sha256, fingerprint, language, text = self._read_state_synthesis()
            audio = self.server.run_state_synthesis(state, state_sha256, fingerprint, language, text)  # type: ignore[attr-defined]
            if not audio or len(audio) > MAX_AUDIO_BYTES:
                raise RuntimeError("invalid state synthesis response")
        except CloneProtocolError as exc:
            self._json(exc.status, {"error": exc.code})
            return
        except BusyError:
            self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "clone_busy"})
            return
        except TimeoutError:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "clone_timeout"})
            return
        except CloneWeightsUnavailableError:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "clone_weights_unavailable"})
            return
        except ConflictError:
            self._json(HTTPStatus.CONFLICT, {"error": "provider_state_incompatible"})
            return
        except StateInvalidError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "state_invalid"})
            return
        except (ValueError, UnicodeDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "state_synthesis_invalid"})
            return
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "state_synthesis_failed"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(audio)

    def _read_state_synthesis(self) -> tuple[bytes, str, str, str, str]:
        if self.headers.get("Transfer-Encoding"):
            raise CloneProtocolError("state_synthesis_invalid")
        raw_length = self.headers.get("Content-Length", "")
        if not re.fullmatch(r"[1-9][0-9]*", raw_length):
            raise CloneProtocolError("state_synthesis_invalid")
        length = int(raw_length)
        if length > MAX_STATE_BYTES or self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/x-safetensors":
            raise CloneProtocolError("state_synthesis_invalid")
        state_sha256 = self.headers.get("X-TeamManager-State-SHA256", "")
        fingerprint = self.headers.get("X-TeamManager-Compatibility-Fingerprint", "")
        if not re.fullmatch(r"[0-9a-f]{64}", state_sha256) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise CloneProtocolError("state_synthesis_invalid")
        language = validate_clone_language(self.headers.get("X-TeamManager-Language", ""))
        encoded_text = self.headers.get("X-TeamManager-Text-B64", "")
        if not encoded_text or len(encoded_text) > self.server.config.max_text_chars * 4:  # type: ignore[attr-defined]
            raise CloneProtocolError("state_synthesis_invalid")
        try:
            padded_text = encoded_text + ("=" * ((4 - len(encoded_text) % 4) % 4))
            text = base64.b64decode(padded_text, altchars=b"-_", validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise CloneProtocolError("state_synthesis_invalid") from exc
        if not text.strip() or len(text) > self.server.config.max_text_chars:  # type: ignore[attr-defined]
            raise CloneProtocolError("state_synthesis_invalid")
        state = self.rfile.read(length)
        if len(state) != length or hashlib.sha256(state).hexdigest() != state_sha256:
            raise CloneProtocolError("state_invalid")
        validate_safetensors(state)
        return state, state_sha256, fingerprint, language, text

    def _read_clone_reference(self) -> tuple[bytes, str]:
        if self.headers.get("Transfer-Encoding"):
            raise CloneProtocolError("reference_wav_invalid")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None or not re.fullmatch(r"[1-9][0-9]*", raw_length):
            raise CloneProtocolError("reference_wav_invalid")
        length = int(raw_length)
        if length > MAX_REFERENCE_BYTES:
            raise CloneProtocolError("reference_too_large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "audio/wav":
            raise CloneProtocolError("reference_wav_invalid")
        expected_hash = self.headers.get("X-TeamManager-Reference-SHA256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise CloneProtocolError("reference_hash_mismatch")
        language = self.headers.get("X-TeamManager-Language", "")
        try:
            language = validate_clone_language(language)
        except ConflictError as exc:
            raise CloneProtocolError("reference_language_unsupported") from exc
        reference = self.rfile.read(length)
        if len(reference) != length:
            raise CloneProtocolError("reference_wav_invalid")
        if hashlib.sha256(reference).hexdigest() != expected_hash:
            raise CloneProtocolError("reference_hash_mismatch")
        validate_clone_reference_wav(reference)
        return reference, language

    def _stream(self, request: dict[str, Any]) -> None:
        synthesizer = self.server.synthesizer  # type: ignore[attr-defined]
        if not callable(getattr(synthesizer, "synthesize_stream", None)):
            self._json(HTTPStatus.NOT_IMPLEMENTED, {"error": "streaming_unsupported"})
            return
        try:
            chunks, sample_rate = self.server.prepare_stream(request)  # type: ignore[attr-defined]
        except StreamingUnsupportedError:
            self._json(HTTPStatus.NOT_IMPLEMENTED, {"error": "streaming_unsupported"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", STREAM_CONTENT_TYPE)
        self.send_header("X-TeamManager-Stream-Version", STREAM_PROTOCOL_VERSION)
        self.send_header("X-Audio-Encoding", "pcm_s16le")
        self.send_header("X-Audio-Sample-Rate", str(sample_rate))
        self.send_header("X-Audio-Channels", "1")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        sequence = 0
        try:
            for pcm in chunks:
                if not pcm or len(pcm) % 2 or len(pcm) > MAX_STREAM_CHUNK_BYTES:
                    raise RuntimeError("invalid streaming PCM chunk")
                self._write_frame(STREAM_FRAME_AUDIO, sequence, pcm)
                sequence += 1
            self._write_frame(STREAM_FRAME_FINAL, sequence, b"")
        except (BrokenPipeError, ConnectionResetError):
            chunks.close()
            return
        except Exception as exc:
            try:
                self._write_frame(STREAM_FRAME_ERROR, sequence, sanitize_error(str(exc)).encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _write_frame(self, frame_type: int, sequence: int, payload: bytes) -> None:
        self.wfile.write(STREAM_FRAME_HEADER.pack(frame_type, sequence, len(payload)))
        if payload:
            self.wfile.write(payload)
        self.wfile.flush()

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("content type must be application/json")
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0:
            raise ValueError("invalid request content length")
        if length > self.server.config.max_body_bytes:  # type: ignore[attr-defined]
            raise ValueError("request body exceeds configured limit")
        body = self.rfile.read(length)
        if not body:
            return {}
        if len(body) > self.server.config.max_body_bytes:  # type: ignore[attr-defined]
            raise ValueError("request body exceeds configured limit")
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def sine_pcm16(duration: float, frequency: float, amplitude: float, sample_rate: int) -> bytes:
    samples = max(1, int(duration * sample_rate))
    pcm = bytearray()
    fade = max(1, min(samples // 8, int(0.03 * sample_rate)))
    for index in range(samples):
        envelope = 1.0
        if index < fade:
            envelope = index / fade
        elif samples - index < fade:
            envelope = (samples - index) / fade
        value = int(32767 * amplitude * envelope * math.sin(2 * math.pi * frequency * index / sample_rate))
        pcm.extend(struct.pack("<h", value))
    return bytes(pcm)


def directory_has_voice_files(path: Path) -> bool:
    return any(
        candidate.is_file()
        for pattern in ("*.wav", "*.safetensors")
        for candidate in path.rglob(pattern)
    )


def tensor_like_to_pcm16(audio: Any) -> bytes:
    if hasattr(audio, "detach"):
        audio = audio.detach()
    if hasattr(audio, "cpu"):
        audio = audio.cpu()
    if hasattr(audio, "numpy"):
        audio = audio.numpy()
    if hasattr(audio, "tolist"):
        audio = audio.tolist()

    pcm = bytearray()
    for sample in audio:
        if isinstance(sample, (list, tuple)):
            sample = sample[0]
        value = float(sample)
        if -1.0 <= value <= 1.0:
            value *= 32767.0
        value = max(-32768, min(32767, int(value)))
        pcm.extend(struct.pack("<h", value))
    return bytes(pcm)


def wav_from_pcm16(pcm: bytes, sample_rate: int) -> bytes:
    out = BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return out.getvalue()


def wav_pcm16(audio: bytes) -> bytes:
    with wave.open(BytesIO(audio), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("WAV must be mono PCM16")
        return wav.readframes(wav.getnframes())


class CloneProtocolError(RuntimeError):
    """Carries one closed clone-route code without echoing rejected input."""

    def __init__(self, code: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def validate_clone_reference_wav(data: bytes) -> None:
    """Applies the desktop's closed RIFF and waveform acceptance contract."""
    if len(data) < 44:
        raise CloneProtocolError("reference_wav_invalid")
    if len(data) > MAX_REFERENCE_BYTES:
        raise CloneProtocolError("reference_too_large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE" or struct.unpack_from("<I", data, 4)[0] + 8 != len(data):
        raise CloneProtocolError("reference_wav_invalid")
    offset = 12
    fmt_seen = False
    data_seen = False
    channels = rate = align = 0
    pcm = b""
    while offset < len(data):
        if len(data) - offset < 8:
            raise CloneProtocolError("reference_wav_invalid")
        kind = data[offset : offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        start = offset + 8
        end = start + size
        padded_end = end + (size & 1)
        if end > len(data) or padded_end > len(data):
            raise CloneProtocolError("reference_wav_invalid")
        if kind == b"fmt ":
            if fmt_seen or size < 16:
                raise CloneProtocolError("reference_wav_invalid")
            fmt_seen = True
            audio_format, channels, rate, byte_rate, align, bits = struct.unpack_from("<HHIIHH", data, start)
            if audio_format != 1 or channels not in (1, 2) or not 8000 <= rate <= 48000 or bits != 16 or align != channels * 2 or byte_rate != rate * align:
                raise CloneProtocolError("reference_format_unsupported")
        elif kind == b"data":
            if data_seen or size == 0:
                raise CloneProtocolError("reference_wav_invalid")
            data_seen = True
            pcm = data[start:end]
        offset = padded_end
    if not fmt_seen or not data_seen or not align or len(pcm) % align:
        raise CloneProtocolError("reference_wav_invalid")
    frames = len(pcm) // align
    if frames < rate or frames > rate * 30:
        raise CloneProtocolError("reference_duration_invalid")
    validate_clone_waveform(pcm, rate, channels)


def validate_clone_waveform(pcm: bytes, rate: int, channels: int) -> None:
    frames = len(pcm) // (channels * 2)
    samples: list[float] = []
    total = 0.0
    for frame in range(frames):
        left = struct.unpack_from("<h", pcm, frame * channels * 2)[0]
        value = left
        if channels == 2:
            right = struct.unpack_from("<h", pcm, (frame * channels + 1) * 2)[0]
            value = int((left + right) / 2)
        samples.append(float(value))
        total += value
    mean = total / len(samples)
    samples = [value - mean for value in samples]
    overall = rms_db(math.sqrt(sum(value * value for value in samples) / len(samples)))
    clipped = longest = run = 0
    for value in samples:
        if abs(value) >= 32760:
            clipped += 1
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    frame_samples = rate // 50
    frame_db: list[float] = []
    active = 0
    for start in range(0, len(samples), frame_samples):
        frame = samples[start : start + frame_samples]
        value = rms_db(math.sqrt(sum(sample * sample for sample in frame) / len(frame)))
        frame_db.append(value)
        if value >= -50:
            active += len(frame)
    if overall < -45 or active * 1000 < rate * 500:
        raise CloneProtocolError("reference_silent")
    if clipped * 1000 >= len(samples) * 5 or longest >= (rate * 10 + 999) // 1000:
        raise CloneProtocolError("reference_clipped")
    frame_db.sort()
    low = frame_db[((len(frame_db) - 1) * 10) // 100]
    high = frame_db[((len(frame_db) - 1) * 90) // 100]
    if low > -25 or high - low < 12:
        raise CloneProtocolError("reference_noisy")


def rms_db(value: float) -> float:
    return float("-inf") if value <= 0 else 20 * math.log10(value / 32768)


def validate_safetensors(data: bytes) -> None:
    """Validates bounded safetensors framing and a contiguous tensor data area."""
    if len(data) < 10 or len(data) > MAX_STATE_BYTES:
        raise StateInvalidError("invalid safetensors size")
    header_length = struct.unpack_from("<Q", data, 0)[0]
    if header_length < 2 or header_length > len(data) - 8 or header_length > 16 * 1024 * 1024:
        raise StateInvalidError("invalid safetensors header length")
    try:
        header = json.loads(data[8 : 8 + header_length].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateInvalidError("invalid safetensors header") from exc
    if not isinstance(header, dict):
        raise StateInvalidError("invalid safetensors header")
    data_size = len(data) - 8 - header_length
    ranges: list[tuple[int, int]] = []
    for key, descriptor in header.items():
        if key == "__metadata__":
            if not isinstance(descriptor, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in descriptor.items()):
                raise StateInvalidError("invalid safetensors metadata")
            continue
        if not isinstance(key, str) or not key or not isinstance(descriptor, dict) or set(descriptor) != {"dtype", "shape", "data_offsets"}:
            raise StateInvalidError("invalid safetensors tensor descriptor")
        offsets = descriptor.get("data_offsets")
        shape = descriptor.get("shape")
        if not isinstance(descriptor.get("dtype"), str) or not isinstance(shape, list) or not all(isinstance(value, int) and value >= 0 for value in shape) or not isinstance(offsets, list) or len(offsets) != 2 or not all(isinstance(value, int) and not isinstance(value, bool) for value in offsets):
            raise StateInvalidError("invalid safetensors tensor descriptor")
        start, end = offsets
        if start < 0 or end < start or end > data_size:
            raise StateInvalidError("invalid safetensors tensor offsets")
        ranges.append((start, end))
    if not ranges:
        raise StateInvalidError("safetensors contains no tensors")
    ranges.sort()
    cursor = 0
    for start, end in ranges:
        if start != cursor:
            raise StateInvalidError("safetensors tensor ranges are not contiguous")
        cursor = end
    if cursor != data_size:
        raise StateInvalidError("safetensors contains trailing data")


def parse_args(argv: list[str]) -> WorkerConfig:
    parser = argparse.ArgumentParser(description="TeamManager Pocket TTS HTTP worker")
    parser.add_argument("--mode", choices=("fake", "real"), default=os.environ.get("POCKET_TTS_MODE", "fake"))
    parser.add_argument("--host", default=os.environ.get("POCKET_TTS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("POCKET_TTS_PORT", "41389")))
    parser.add_argument("--model-dir", default=os.environ.get("POCKET_TTS_MODEL_DIR", DEFAULT_MODEL_DIR))
    parser.add_argument("--voice-dir", default=os.environ.get("POCKET_TTS_VOICE_DIR", DEFAULT_VOICE_DIR))
    parser.add_argument("--default-voice", default=os.environ.get("POCKET_TTS_DEFAULT_VOICE", "alba"))
    parser.add_argument("--language", default=os.environ.get("POCKET_TTS_LANGUAGE", "english"))
    parser.add_argument("--max-body-bytes", type=int, default=int(os.environ.get("POCKET_TTS_MAX_BODY_BYTES", str(DEFAULT_MAX_BODY_BYTES))))
    parser.add_argument("--max-text-chars", type=int, default=int(os.environ.get("POCKET_TTS_MAX_TEXT_CHARS", str(DEFAULT_MAX_TEXT_CHARS))))
    parser.add_argument("--request-timeout-ms", type=int, default=int(os.environ.get("POCKET_TTS_REQUEST_TIMEOUT_MS", str(DEFAULT_REQUEST_TIMEOUT_MS))))
    parser.add_argument("--max-queue", type=int, default=int(os.environ.get("POCKET_TTS_MAX_QUEUE", str(DEFAULT_MAX_QUEUE))))
    parser.add_argument("--fake-delay-ms", type=int, default=int(os.environ.get("POCKET_TTS_FAKE_DELAY_MS", "0")))
    parser.add_argument("--cpu-threads", type=int, default=int(os.environ.get("POCKET_TTS_CPU_THREADS", "2")))
    parser.add_argument("--state-compatibility-manifest", default="")
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("Pocket worker host must be localhost")
    if args.port < 0 or args.port > 65535:
        parser.error("port must be between 0 and 65535")
    if args.max_body_bytes < 2 or args.max_text_chars < 1 or args.request_timeout_ms < 1 or args.max_queue < 0 or args.cpu_threads < 1:
        parser.error("worker limits must be positive and max_queue must be non-negative")
    return WorkerConfig(
        mode=args.mode,
        host=args.host,
        port=args.port,
        model_dir=args.model_dir,
        voice_dir=args.voice_dir,
        default_voice=args.default_voice,
        language=args.language,
        max_body_bytes=args.max_body_bytes,
        max_text_chars=args.max_text_chars,
        request_timeout_ms=args.request_timeout_ms,
        max_queue=args.max_queue,
        fake_delay_ms=args.fake_delay_ms,
        cpu_threads=args.cpu_threads,
        state_compatibility_manifest=args.state_compatibility_manifest,
    )


def main(argv: list[str]) -> int:
    config = parse_args(argv)
    # Set supported numerical runtime caps before importing/loading Pocket.
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = str(config.cpu_threads)
    synthesizer: FakeSynthesizer | RealPocketSynthesizer
    if config.mode == "real":
        compatibility = load_activated_state_compatibility(config.state_compatibility_manifest)
        synthesizer = RealPocketSynthesizer(config, activated_compatibility=compatibility)
    else:
        synthesizer = FakeSynthesizer()

    server = PocketWorkerServer((config.host, config.port), PocketWorkerHandler, synthesizer, config)
    actual_host, actual_port = server.server_address[:2]
    print(
        json.dumps(
            {
                "event": "listening",
                "mode": config.mode,
                "worker_version": WORKER_VERSION,
                "capabilities": list(WORKER_CAPABILITIES),
                "base_url": f"http://{actual_host}:{actual_port}",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def sanitize_error(message: str, limit: int = 160) -> str:
    trimmed = " ".join(str(message or "").replace("\n", " ").replace("\r", " ").split())
    if not trimmed:
        return ""
    redacted: list[str] = []
    for field in trimmed.split(" "):
        lower = field.lower()
        if "/" in field or "\\" in field:
            redacted.append("[redacted-path]")
        elif any(token in lower for token in ("token", "api_key", "apikey", "authorization", "bearer")):
            redacted.append("[redacted-secret]")
        elif "{" in field or "}" in field or "\"text\"" in lower or "request=" in lower or "body=" in lower:
            redacted.append("[redacted-body]")
        else:
            redacted.append(field[:96])
    bounded = " ".join(redacted)
    return bounded[:limit]


def validate_language(language: str) -> str:
    normalized = language.strip().lower()
    if normalized not in SUPPORTED_LANGUAGES or not re.fullmatch(r"[a-z0-9_-]+", normalized):
        raise ConflictError("unsupported Pocket language")
    return normalized


def validate_clone_language(language: str) -> str:
    normalized = language.strip().lower()
    if normalized not in CLONE_LANGUAGES or not re.fullmatch(r"[a-z0-9_-]+", normalized):
        raise ConflictError("unsupported Pocket clone language")
    return normalized


def finite_float(value: Any, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def validate_request(request: dict[str, Any]) -> None:
    if "stream" in request and not isinstance(request["stream"], bool):
        raise ValueError("stream must be a boolean")
    if request.get("radio_fx"):
        raise ValueError("radio_fx is applied by TeamManager and is not a Pocket inference parameter")
    for unsupported in ("quality_preset", "rate", "speed", "radio_fx_preset", "background_noise_amount", "radio_chatter_amount"):
        if request.get(unsupported) not in (None, "", 0, 0.0, False):
            raise ValueError(f"{unsupported} is unsupported by the Pocket inference adapter")
    validate_language(str(request.get("language") or "english"))
    temperature = finite_float(request.get("temperature", 0.7), "temperature")
    if temperature <= 0:
        raise ValueError("temperature must be greater than zero")
    try:
        lsd_decode_steps = int(request.get("lsd_decode_steps", 1) or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("lsd_decode_steps must be an integer") from exc
    if lsd_decode_steps < 1:
        raise ValueError("lsd_decode_steps must be at least one")
    if finite_float(request.get("eos_threshold", -4.0), "eos_threshold") > 0:
        raise ValueError("eos_threshold must be zero or negative")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
