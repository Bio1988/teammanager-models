#!/usr/bin/env python3
"""Fail-closed validation for a published TeamManager model manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def reject_duplicate_names(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def validate_english_only_catalog(manifest: Path) -> None:
    value = json.loads(manifest.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_names)
    bundles = value["assets"]["pocket_bundles"]
    default_windows = bundles["default_windows"]
    if default_windows["default_language"] != "english":
        raise ValueError("default Pocket language must be English")
    if default_windows["english_model"]["layout"]["language"] != "english":
        raise ValueError("default Pocket model must be English")
    clone_languages = default_windows["state_compatibility_model"]["clone_languages"]
    if [entry["language"] for entry in clone_languages] != ["english"]:
        raise ValueError("clone compatibility must contain exactly English")
    language_packs = bundles["language_packs"]
    if any(pack["languages"] != ["english"] for pack in language_packs):
        raise ValueError("language packs must contain exactly English")
    archives = [archive for pack in language_packs for archive in pack["archives"]]
    archives.extend(bundles["optional"])
    if not archives or any(archive["layout"]["language"] != "english" for archive in archives):
        raise ValueError("downloadable Pocket archives must be English")


def verify(manifest: Path, signature: Path, sha256_sidecar: Path, public_key: Path) -> None:
    if signature.stat().st_size != 64:
        raise ValueError("Ed25519 detached signature must be exactly 64 bytes")
    expected_sidecar = hashlib.sha256(manifest.read_bytes()).hexdigest().encode("ascii") + b"\n"
    if sha256_sidecar.read_bytes() != expected_sidecar:
        raise ValueError("SHA-256 sidecar must be lowercase hexadecimal plus one newline")
    subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key), "-rawin",
         "-in", str(manifest), "-sigfile", str(signature)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    validate_english_only_catalog(manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--sha256", dest="sha256_sidecar", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()
    verify(args.manifest, args.signature, args.sha256_sidecar, args.public_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
