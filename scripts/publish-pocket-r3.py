#!/usr/bin/env python3
"""Build and sign the immutable TeamManager Pocket R3 repair authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


BASE_RUNTIME_SHA256 = "c1762f24c642c592c08768ea8d669ffc348a2fad7a2907ff27502f956fb921b4"
OFFICIAL_ALBA_SHA256 = "69c32db63ca56843d994f81f343f62e0bf2d73f7e4c9bc73e44bb1110b1d8845"
BASE_RUNTIME_ROOT = "pocket-runtime-win-cpu-v2.1.0/"
R3_RUNTIME_ROOT = "pocket-runtime-win-cpu-v2.1.0-r3/"
R3_VOICE_ROOT = "pocket-voice-alba-v2.1.0-r3/"
R3_RELEASE = "pocket-tts-v2.1.0-r3"
R3_RUNTIME_FILE = "pocket-runtime-win-cpu-v2.1.0-r3.zip"
R3_VOICE_FILE = "pocket-voice-alba-v2.1.0-r3.zip"
R3_REVISION = "teammanager-pocket-r3"
FIXED_ZIP_TIME = (2026, 7, 24, 0, 0, 0)
REQUIRED_WORKER_MARKERS = (
    'WORKER_VERSION = "0.3.0"',
    'CLONE_PATH = "/v1/voices/clone"',
    'STATE_SYNTH_PATH = "/v1/audio/speech/state"',
    '"voice-clone-v1"',
    '"voice-state-synthesis-v1"',
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_info(name: str, *, directory: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.create_system = 3
    info.external_attr = ((0o755 if directory else 0o644) << 16)
    if directory:
        info.external_attr |= 0x10
    return info


def build_runtime(base_runtime: Path, worker: Path, output: Path) -> None:
    if sha256(base_runtime) != BASE_RUNTIME_SHA256:
        raise ValueError("base Pocket runtime digest is not canonical")
    worker_bytes = worker.read_bytes()
    worker_text = worker_bytes.decode("utf-8")
    for marker in REQUIRED_WORKER_MARKERS:
        if marker not in worker_text:
            raise ValueError(f"worker is missing required R3 marker: {marker}")

    worker_member = BASE_RUNTIME_ROOT + "worker.py"
    seen_worker = False
    with zipfile.ZipFile(base_runtime) as source, zipfile.ZipFile(
        output, "w", allowZip64=True
    ) as target:
        for source_info in source.infolist():
            if not source_info.filename.startswith(BASE_RUNTIME_ROOT):
                raise ValueError(f"unexpected base runtime member: {source_info.filename}")
            suffix = source_info.filename[len(BASE_RUNTIME_ROOT):]
            target_name = R3_RUNTIME_ROOT + suffix
            if source_info.is_dir():
                target.writestr(zip_info(target_name, directory=True), b"")
                continue
            target_info = zip_info(target_name)
            target_info.compress_type = source_info.compress_type
            if source_info.filename == worker_member:
                seen_worker = True
                target.writestr(target_info, worker_bytes, compresslevel=9)
                continue
            if suffix == "bundle-build.json":
                metadata = json.loads(source.read(source_info).decode("utf-8"))
                metadata["state_compatibility_runtime"] = {
                    "schema": "pocket-state-runtime-v1",
                    "pocket_package_version": "2.1.0",
                    "python_version": "3.11.9",
                    "python_abi": "cp311-win_amd64",
                    "torch_version": "2.5.1+cpu",
                    "torch_build": "cpu-cp311-win_amd64",
                    "worker_state_contract_version": "pocket-worker-state-v1",
                    "state_export_api": "pocket.export_model_state-v1",
                    "state_format": "safetensors-v1",
                }
                target.writestr(
                    target_info,
                    (json.dumps(metadata, indent=2) + "\n").encode("utf-8"),
                    compresslevel=9,
                )
                continue
            with source.open(source_info) as reader, target.open(target_info, "w") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
    if not seen_worker:
        raise ValueError("base Pocket runtime has no TeamManager worker")


def build_voice(alba: Path, output: Path) -> None:
    if sha256(alba) != OFFICIAL_ALBA_SHA256:
        raise ValueError("Alba bytes do not match the pinned official Kyutai state")
    notice = (
        "Alba is the official Pocket TTS English catalog voice state.\n"
        "Source: kyutai/pocket-tts-without-voice-cloning, immutable revision\n"
        "e041936c75475d350b405bc870bcf7c22da4e9e6.\n"
        "Voice state SHA-256: " + OFFICIAL_ALBA_SHA256 + "\n"
        "License: CC0-1.0 catalog voice state.\n"
    ).encode("utf-8")
    provenance = json.dumps(
        {
            "schema": "teammanager-pocket-catalog-voice-v1",
            "voice_id": "alba",
            "upstream": "kyutai/pocket-tts-without-voice-cloning",
            "revision": "e041936c75475d350b405bc870bcf7c22da4e9e6",
            "member": "languages/english/embeddings/alba.safetensors",
            "sha256": OFFICIAL_ALBA_SHA256,
        },
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        archive.writestr(
            zip_info(R3_VOICE_ROOT + "THIRD_PARTY_NOTICES.md"),
            notice,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
        archive.writestr(
            zip_info(R3_VOICE_ROOT + "upstream-source.json"),
            provenance,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
        state_info = zip_info(R3_VOICE_ROOT + "voice/alba.safetensors")
        state_info.compress_type = zipfile.ZIP_STORED
        with alba.open("rb") as reader, archive.open(state_info, "w") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)


def update_manifest(
    source: Path,
    runtime: Path,
    voice: Path,
    generated: str,
    output: Path,
) -> None:
    manifest = json.loads(source.read_text(encoding="utf-8"))
    bundle = manifest["assets"]["pocket_bundles"]["default_windows"]
    manifest["generated"] = generated
    bundle["package_revision"] = R3_REVISION

    runtime_asset = bundle["runtime"]
    runtime_asset.update(
        {
            "package_revision": R3_REVISION,
            "release_tag": R3_RELEASE,
            "file": R3_RUNTIME_FILE,
            "url": f"{{base_url}}/Max/teammanager-models/releases/download/{R3_RELEASE}/{R3_RUNTIME_FILE}",
            "sha256": sha256(runtime),
            "size_bytes": runtime.stat().st_size,
            "extracted_root": R3_RUNTIME_ROOT.rstrip("/"),
        }
    )
    voice_asset = bundle["catalog_voice"]
    voice_asset.update(
        {
            "package_revision": R3_REVISION,
            "release_tag": R3_RELEASE,
            "file": R3_VOICE_FILE,
            "url": f"{{base_url}}/Max/teammanager-models/releases/download/{R3_RELEASE}/{R3_VOICE_FILE}",
            "sha256": sha256(voice),
            "size_bytes": voice.stat().st_size,
            "extracted_root": R3_VOICE_ROOT.rstrip("/"),
            "attribution": (
                "Official Alba catalog voice state from Kyutai Pocket TTS, "
                "immutable upstream revision e041936c75475d350b405bc870bcf7c22da4e9e6."
            ),
        }
    )
    manifest["checksums"]["files"][R3_RUNTIME_FILE] = sha256(runtime)
    manifest["checksums"]["files"][R3_VOICE_FILE] = sha256(voice)
    output.write_bytes(
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )


def sign_manifest(
    manifest: Path, signing_key: Path, public_key: Path, output_dir: Path
) -> tuple[Path, Path, Path]:
    versioned = output_dir / "teammanager-model-manifest-v3.json"
    shutil.copyfile(manifest, versioned)
    signature = versioned.with_suffix(versioned.suffix + ".sig")
    subprocess.run(
        [
            "openssl", "pkeyutl", "-sign", "-inkey", str(signing_key),
            "-rawin", "-in", str(versioned), "-out", str(signature),
        ],
        check=True,
    )
    if signature.stat().st_size != 64:
        raise ValueError("Ed25519 signature must be exactly 64 bytes")
    subprocess.run(
        [
            "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
            "-rawin", "-in", str(versioned), "-sigfile", str(signature),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    sidecar = versioned.with_suffix(versioned.suffix + ".sha256")
    sidecar.write_text(sha256(versioned) + "\n", encoding="ascii", newline="\n")
    return versioned, signature, sidecar


def publish(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runtime = args.output_dir / R3_RUNTIME_FILE
    voice = args.output_dir / R3_VOICE_FILE
    unsigned_manifest = args.output_dir / "manifest.r3.json"
    build_runtime(args.base_runtime, args.worker, runtime)
    build_voice(args.alba, voice)
    update_manifest(args.manifest, runtime, voice, args.generated, unsigned_manifest)
    versioned, signature, sidecar = sign_manifest(
        unsigned_manifest, args.signing_key, args.public_key, args.output_dir
    )
    args.updated_manifest.write_bytes(versioned.read_bytes())
    args.updated_signature.write_bytes(signature.read_bytes())
    args.updated_sidecar.write_bytes(sidecar.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--alba", type=Path, required=True)
    parser.add_argument("--generated", required=True)
    parser.add_argument("--signing-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--updated-manifest", type=Path, required=True)
    parser.add_argument("--updated-signature", type=Path, required=True)
    parser.add_argument("--updated-sidecar", type=Path, required=True)
    publish(parser.parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
