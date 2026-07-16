#!/usr/bin/env python3
"""Build and sign the English Pocket clone compatibility authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path


CANONICAL_RELEASE = "pocket-tts-v2.1.0"
MODEL_ARCHIVE = "pocket-model-en-v2.1.0.zip"
RUNTIME_ARCHIVE = "pocket-runtime-win-cpu-v2.1.0.zip"
VOICE_ARCHIVE = "pocket-voice-alba-v2.1.0.zip"
MODEL_MEMBER = "pocket-model-en-v2.1.0/model/weights/model.safetensors"
CONFIG_MEMBER = "pocket-model-en-v2.1.0/model/config.yaml"
ENGLISH_MODEL_REVISION = "39592ff23c9ef80098bb74895d104c26275fe2c9"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/+:-]{0,127}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def reject_duplicate_names(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_member_sha256(archive: Path, member: str) -> str:
    digest = hashlib.sha256()
    with zipfile.ZipFile(archive) as bundle:
        info = bundle.getinfo(member)
        if info.is_dir() or info.file_size < 1 or info.file_size > 1024 * 1024 * 1024:
            raise ValueError(f"canonical archive member is invalid: {member}")
        with bundle.open(info) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _closed(value: object, keys: tuple[str, ...], name: str) -> dict[str, object]:
    if not isinstance(value, dict) or tuple(value) != keys:
        raise ValueError(f"{name} must contain exactly {', '.join(keys)} in order")
    return value


def validate_state_compatibility_model(value: object) -> dict[str, object]:
    model = _closed(value, (
        "schema", "provider_kind", "pocket_package_version", "model_id",
        "model_revision", "model_sha256", "model_config_sha256", "clone_languages",
    ), "state_compatibility_model")
    if model["schema"] != "pocket-state-model-v1" or model["provider_kind"] != "pocket_tts_managed":
        raise ValueError("state_compatibility_model identity is invalid")
    for key in ("pocket_package_version", "model_id", "model_revision"):
        if not isinstance(model[key], str) or not IDENTIFIER.fullmatch(model[key]):
            raise ValueError(f"{key} is invalid")
    for key in ("model_sha256", "model_config_sha256"):
        if not isinstance(model[key], str) or not HEX64.fullmatch(model[key]):
            raise ValueError(f"{key} is invalid")
    rows = model["clone_languages"]
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("clone_languages must contain exactly English")
    row = _closed(rows[0], ("language", "cloning_weights_sha256"), "clone language")
    if row["language"] != "english" or not isinstance(row["cloning_weights_sha256"], str) or not HEX64.fullmatch(row["cloning_weights_sha256"]):
        raise ValueError("English clone language row is invalid")
    if row["cloning_weights_sha256"] != model["model_sha256"]:
        raise ValueError("English cloning weights must be the canonical model bytes")
    return model


def _asset(bundle: dict[str, object], name: str, expected_file: str) -> dict[str, object]:
    value = bundle.get(name)
    if not isinstance(value, dict) or value.get("release_tag") != CANONICAL_RELEASE or value.get("file") != expected_file:
        raise ValueError(f"canonical {name} asset identity is invalid")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        raise ValueError(f"canonical {name} archive digest is invalid")
    return value


def build_model(manifest: dict[str, object], root: Path) -> dict[str, object]:
    bundle = manifest["assets"]["pocket_bundles"]["default_windows"]
    if not isinstance(bundle, dict) or bundle.get("model_revision") != ENGLISH_MODEL_REVISION:
        raise ValueError("canonical English bundle revision is invalid")
    runtime = _asset(bundle, "runtime", RUNTIME_ARCHIVE)
    model_asset = _asset(bundle, "english_model", MODEL_ARCHIVE)
    voice = _asset(bundle, "catalog_voice", VOICE_ARCHIVE)
    archives = {
        "runtime": root / RUNTIME_ARCHIVE,
        "english_model": root / MODEL_ARCHIVE,
        "catalog_voice": root / VOICE_ARCHIVE,
    }
    for name, asset in (("runtime", runtime), ("english_model", model_asset), ("catalog_voice", voice)):
        archive = archives[name]
        if not archive.is_file() or sha256(archive) != asset["sha256"]:
            raise ValueError(f"canonical {name} archive bytes are invalid")
    model_hash = zip_member_sha256(archives["english_model"], MODEL_MEMBER)
    config_hash = zip_member_sha256(archives["english_model"], CONFIG_MEMBER)
    return validate_state_compatibility_model({
        "schema": "pocket-state-model-v1",
        "provider_kind": "pocket_tts_managed",
        "pocket_package_version": model_asset["package_version"],
        "model_id": "kyutai/pocket-tts",
        "model_revision": ENGLISH_MODEL_REVISION,
        "model_sha256": model_hash,
        "model_config_sha256": config_hash,
        "clone_languages": [{"language": "english", "cloning_weights_sha256": model_hash}],
    })


def verify_signature(public_key: Path, manifest: Path, signature: Path) -> None:
    subprocess.run([
        "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
        "-rawin", "-in", str(manifest), "-sigfile", str(signature),
    ], check=True, stdout=subprocess.DEVNULL)


def publish(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_names)
    model = build_model(manifest, args.artifact_root)
    manifest["assets"]["pocket_bundles"]["default_windows"]["state_compatibility_model"] = model
    output = args.output_dir / f"teammanager-model-manifest-v{manifest['version']}.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    signature = output.with_suffix(output.suffix + ".sig")
    subprocess.run([
        "openssl", "pkeyutl", "-sign", "-inkey", str(args.signing_key),
        "-rawin", "-in", str(output), "-out", str(signature),
    ], check=True)
    if signature.stat().st_size != 64:
        raise ValueError("Ed25519 detached signature must be exactly 64 bytes")
    verify_signature(args.public_key, output, signature)
    output.with_suffix(output.suffix + ".sha256").write_text(sha256(output) + "\n", encoding="ascii", newline="\n")
    args.updated_manifest.write_bytes(output.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--signing-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--updated-manifest", type=Path, required=True)
    args = parser.parse_args()
    publish(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
