#!/usr/bin/env python3
"""Build and sign the immutable managed Whisper v1.9.1 authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path


SCHEMA = "teammanager-managed-whisper-authority-v1"
DOMAIN = b"TeamManager managed Whisper authority v1\x00"
AUTHORITY_RELEASE = "whisper-authority-v1.9.1-r1"
RUNTIME_RELEASE = "whispercpp-v1.9.1"
MODEL_RELEASE = "whisper-q5-v1"
PLATFORM = "windows-amd64"
MANIFEST_FILE = "teammanager-whisper-runtime-only-win-x64-v1.9.1.manifest-v3.json"
RUNTIME_FILE = "teammanager-whisper-runtime-only-win-x64-v1.9.1.zip"
MODEL_FILE = "ggml-base-q5_1.bin"
OUTPUT_FILE = "teammanager-whisper-authority-v1.json"
REVIEWED_PUBLIC_KEY_HEX = "e6a8a309e98a5f38f4c40938c26c216ecc75980215a365c7610386acedf4cccd"
REVIEWED_PUBLIC_KEY_DER_SHA256 = "0f7cbba3263a46429f7edbb0e7c42cea5eaa6c111193fded4c74aca80db94537"
REVIEWED_MANIFEST = (3997, "580054f45ef7918837be16862e3fbd09a30e73f768fc2c305112b1f2ee00d232")
REVIEWED_RUNTIME = (4505044, "6ac6eecf51eb0e84bf091bc06d7c2dbb700fef3e4b4e38bb6de1b852b47ba0b6")
REVIEWED_MODEL = (59707625, "422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898")
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


def _closed(value: object, keys: tuple[str, ...], name: str) -> dict[str, object]:
    if not isinstance(value, dict) or tuple(value) != keys:
        raise ValueError(f"{name} must contain exactly {', '.join(keys)} in order")
    return value


def _identity(value: object, digest: str, name: str) -> None:
    if value != "sha256:" + digest:
        raise ValueError(f"{name} identity does not match its SHA-256")


def validate_runtime_members(runtime_row: dict[str, object], runtime: Path) -> None:
    rows = runtime_row["members"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("runtime member inventory is empty")
    expected: dict[str, tuple[int, str]] = {}
    for value in rows:
        row = _closed(value, ("path", "size_bytes", "sha256"), "runtime member")
        name, size, digest = row["path"], row["size_bytes"], row["sha256"]
        if (not isinstance(name, str) or not name or name.startswith(("/", "\\"))
                or ".." in Path(name).parts or "\\" in name or name in expected):
            raise ValueError("runtime member path is invalid or duplicated")
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise ValueError(f"runtime member size is invalid: {name}")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise ValueError(f"runtime member SHA-256 is invalid: {name}")
        expected[name] = (size, digest)
    with zipfile.ZipFile(runtime) as archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        if len(files) != len(archive.infolist()) or {info.filename for info in files} != set(expected):
            raise ValueError("runtime archive inventory does not match the release manifest")
        if len(files) != len(expected):
            raise ValueError("runtime archive contains duplicate member names")
        for info in files:
            size, digest = expected[info.filename]
            actual = hashlib.sha256()
            with archive.open(info) as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    actual.update(chunk)
            if info.file_size != size or actual.hexdigest() != digest:
                raise ValueError(f"runtime archive member bytes are invalid: {info.filename}")


def validate_release_manifest(path: Path, runtime: Path, model: Path) -> dict[str, object]:
    reviewed = (
        (path, REVIEWED_MANIFEST, "release manifest"),
        (runtime, REVIEWED_RUNTIME, "runtime archive"),
        (model, REVIEWED_MODEL, "baseline model"),
    )
    for asset, (size, digest), name in reviewed:
        if asset.stat().st_size != size or sha256(asset) != digest:
            raise ValueError(f"{name} does not match the reviewed Forgejo asset")
    manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_names)
    manifest = _closed(manifest, (
        "schema_version", "release_identity", "release_version", "platform",
        "runtime", "baseline_model", "optional_models",
    ), "schema-v3 release manifest")
    if manifest["schema_version"] != 3 or manifest["release_version"] != RUNTIME_RELEASE or manifest["platform"] != PLATFORM:
        raise ValueError("schema-v3 release identity is invalid")
    runtime_row = _closed(manifest["runtime"], (
        "archive_identity", "file_name", "size_bytes", "sha256",
        "server_executable", "members",
    ), "runtime")
    model_row = _closed(manifest["baseline_model"], (
        "id", "release_identity", "release_version", "file_name", "size_bytes", "sha256",
    ), "baseline_model")
    runtime_hash, model_hash = sha256(runtime), sha256(model)
    if (runtime_row["file_name"] != RUNTIME_FILE or runtime_row["size_bytes"] != runtime.stat().st_size
            or runtime_row["sha256"] != runtime_hash
            or runtime_row["server_executable"] != "Release/whisper-server.exe"):
        raise ValueError("canonical runtime archive bytes are invalid")
    if model_row["id"] != "base-q5_1" or model_row["release_version"] != MODEL_RELEASE or model_row["file_name"] != MODEL_FILE or model_row["size_bytes"] != model.stat().st_size or model_row["sha256"] != model_hash:
        raise ValueError("canonical baseline model bytes are invalid")
    _identity(manifest["release_identity"], runtime_hash, "release")
    _identity(runtime_row["archive_identity"], runtime_hash, "runtime")
    _identity(model_row["release_identity"], model_hash, "baseline model")
    validate_runtime_members(runtime_row, runtime)
    return manifest


def release_url(host: str, tag: str, file: str) -> str:
    if host == "forgejo":
        return f"https://forgejo.g-grp.com/Max/teammanager-models/releases/download/{tag}/{file}"
    github_file = file if file.startswith(tag + "-") else tag + "-" + file
    return f"https://github.com/Bio1988/teammanager-models/releases/download/{tag}/{github_file}"


def public_key_identity(public_key: Path) -> tuple[str, str]:
    der = subprocess.run(
        ["openssl", "pkey", "-pubin", "-in", str(public_key), "-outform", "DER"],
        check=True, capture_output=True,
    ).stdout
    if len(der) < 32 or der[-32:].hex() != REVIEWED_PUBLIC_KEY_HEX:
        raise ValueError("public key is not the reviewed TeamManager model-manifest key")
    fingerprint = hashlib.sha256(der).hexdigest()
    if fingerprint != REVIEWED_PUBLIC_KEY_DER_SHA256:
        raise ValueError("reviewed public-key fingerprint mismatch")
    return der[-32:].hex(), fingerprint


def build_authority(manifest_path: Path, runtime_path: Path, model_path: Path, public_key: Path) -> dict[str, object]:
    manifest = validate_release_manifest(manifest_path, runtime_path, model_path)
    public_hex, fingerprint = public_key_identity(public_key)
    runtime = manifest["runtime"]
    model = manifest["baseline_model"]
    return {
        "schema": SCHEMA,
        "authority_release": AUTHORITY_RELEASE,
        "runtime_release": RUNTIME_RELEASE,
        "platform": PLATFORM,
        "signing": {
            "algorithm": "Ed25519",
            "key_id": "sha256:" + fingerprint,
            "public_key_hex": public_hex,
            "message_domain": DOMAIN[:-1].decode("ascii"),
        },
        "release_manifest": {
            "schema_version": 3,
            "file_name": MANIFEST_FILE,
            "size_bytes": manifest_path.stat().st_size,
            "sha256": sha256(manifest_path),
            "forgejo_url": release_url("forgejo", RUNTIME_RELEASE, MANIFEST_FILE),
            "github_url": release_url("github", RUNTIME_RELEASE, MANIFEST_FILE),
        },
        "runtime": {
            "release_identity": "sha256:" + runtime["sha256"],
            "file_name": RUNTIME_FILE,
            "size_bytes": runtime_path.stat().st_size,
            "sha256": sha256(runtime_path),
            "forgejo_url": release_url("forgejo", RUNTIME_RELEASE, RUNTIME_FILE),
            "github_url": release_url("github", RUNTIME_RELEASE, RUNTIME_FILE),
        },
        "baseline_model": {
            "id": "base-q5_1",
            "release": MODEL_RELEASE,
            "release_identity": "sha256:" + model["sha256"],
            "file_name": MODEL_FILE,
            "size_bytes": model_path.stat().st_size,
            "sha256": sha256(model_path),
            "forgejo_url": release_url("forgejo", MODEL_RELEASE, MODEL_FILE),
            "github_url": release_url("github", MODEL_RELEASE, MODEL_FILE),
        },
    }


def authority_bytes(authority: dict[str, object]) -> bytes:
    return (json.dumps(authority, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def verify_signature(public_key: Path, authority: Path, signature: Path) -> None:
    if signature.stat().st_size != 64:
        raise ValueError("Ed25519 detached signature must be exactly 64 bytes")
    preimage = authority.parent / ("." + authority.name + ".verification-preimage")
    try:
        preimage.write_bytes(DOMAIN + authority.read_bytes())
        subprocess.run([
            "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
            "-rawin", "-in", str(preimage), "-sigfile", str(signature),
        ], check=True, stdout=subprocess.DEVNULL)
    finally:
        preimage.unlink(missing_ok=True)


def validate_published(authority: Path, signature: Path, sidecar: Path,
                       manifest: Path, runtime: Path, model: Path, public_key: Path) -> None:
    parsed = json.loads(authority.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_names)
    expected = build_authority(manifest, runtime, model, public_key)
    if authority.read_bytes() != authority_bytes(expected) or parsed != expected:
        raise ValueError("authority is not the exact closed deterministic release object")
    expected_sidecar = (sha256(authority) + "\n").encode("ascii")
    if sidecar.read_bytes() != expected_sidecar:
        raise ValueError("authority SHA-256 sidecar is invalid")
    verify_signature(public_key, authority, signature)


def publish(args: argparse.Namespace) -> None:
    authority = build_authority(args.release_manifest, args.runtime, args.model, args.public_key)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / OUTPUT_FILE
    output.write_bytes(authority_bytes(authority))
    preimage = args.output_dir / ".whisper-authority-signing-preimage"
    signature = output.with_suffix(output.suffix + ".sig")
    try:
        preimage.write_bytes(DOMAIN + output.read_bytes())
        subprocess.run([
            "openssl", "pkeyutl", "-sign", "-inkey", str(args.signing_key),
            "-rawin", "-in", str(preimage), "-out", str(signature),
        ], check=True)
        if signature.stat().st_size != 64:
            raise ValueError("Ed25519 detached signature must be exactly 64 bytes")
    finally:
        preimage.unlink(missing_ok=True)
    output.with_suffix(output.suffix + ".sha256").write_text(sha256(output) + "\n", encoding="ascii", newline="\n")
    validate_published(
        output, signature, output.with_suffix(output.suffix + ".sha256"),
        args.release_manifest, args.runtime, args.model, args.public_key,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-authority", type=Path)
    parser.add_argument("--signature", type=Path)
    parser.add_argument("--sidecar", type=Path)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--signing-key", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.validate_authority:
        if not args.signature or not args.sidecar or args.signing_key or args.output_dir:
            parser.error("validation requires --signature and --sidecar, without publication options")
        validate_published(
            args.validate_authority, args.signature, args.sidecar,
            args.release_manifest, args.runtime, args.model, args.public_key,
        )
    else:
        if not args.signing_key or not args.output_dir or args.signature or args.sidecar:
            parser.error("publication requires --signing-key and --output-dir")
        publish(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
