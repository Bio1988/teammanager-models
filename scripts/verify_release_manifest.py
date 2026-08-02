#!/usr/bin/env python3
"""Fail-closed validation for the exact TeamManager Pocket R3.2 manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def reject_duplicate_names(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> object:
    raise ValueError(f"invalid JSON constant: {value}")


def object_at(value: object, where: str, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    actual = set(value)
    if actual != keys:
        raise ValueError(f"{where} members differ: missing={sorted(keys - actual)!r} unknown={sorted(actual - keys)!r}")
    return value


def string_at(value: object, where: str, expected: str | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where} must be a non-empty string")
    if expected is not None and value != expected:
        raise ValueError(f"{where} must be {expected!r}")
    return value


def integer_at(value: object, where: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{where} must be a positive integer")
    return value


def boolean_at(value: object, where: str, expected: bool) -> None:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"{where} must be {expected!r}")


def sha_at(value: object, where: str) -> None:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise ValueError(f"{where} must be lowercase SHA-256")


def string_fields(value: dict[str, object], where: str, names: tuple[str, ...]) -> None:
    for name in names:
        string_at(value[name], f"{where}.{name}")


def validate_layout(value: object, where: str, kind: str, optional: bool) -> None:
    layouts = {
        "runtime": {"python_path", "worker_path"},
        "voice": {"voice_dir", "default_voice_id"},
        "model": {"model_dir", "config_path", "language"} | (set() if optional else {"hf_cache_dir"}),
    }
    layout = object_at(value, where, layouts[kind])
    string_fields(layout, where, tuple(layouts[kind]))
    if kind == "model":
        string_at(layout["language"], f"{where}.language", "english")


def validate_archive(value: object, where: str, kind: str, optional: bool = False) -> None:
    common = {"id", "kind", "platform", "package_version", "package_revision", "release_tag", "file", "url", "sha256", "size_bytes", "license", "attribution", "extracted_root", "layout"}
    keys = common | ({"model_revision"} if kind == "model" else set()) | ({"optional"} if optional else {"default"})
    archive = object_at(value, where, keys)
    string_fields(archive, where, tuple(common - {"sha256", "size_bytes", "layout"}))
    string_at(archive["kind"], f"{where}.kind", kind)
    string_at(archive["platform"], f"{where}.platform", "windows-amd64-cpu")
    sha_at(archive["sha256"], f"{where}.sha256")
    integer_at(archive["size_bytes"], f"{where}.size_bytes")
    if kind == "model":
        string_at(archive["model_revision"], f"{where}.model_revision")
    boolean_at(archive["optional"] if optional else archive["default"], f"{where}.{'optional' if optional else 'default'}", True)
    validate_layout(archive["layout"], f"{where}.layout", kind, optional)


def validate_state_model(value: object) -> None:
    state = object_at(value, "assets.pocket_bundles.default_windows.state_compatibility_model", {"schema", "provider_kind", "pocket_package_version", "model_id", "model_revision", "model_sha256", "model_config_sha256", "clone_languages"})
    string_fields(state, "assets.pocket_bundles.default_windows.state_compatibility_model", ("schema", "provider_kind", "pocket_package_version", "model_id", "model_revision"))
    string_at(state["schema"], "assets.pocket_bundles.default_windows.state_compatibility_model.schema", "pocket-state-model-v1")
    string_at(state["provider_kind"], "assets.pocket_bundles.default_windows.state_compatibility_model.provider_kind", "pocket_tts_managed")
    sha_at(state["model_sha256"], "assets.pocket_bundles.default_windows.state_compatibility_model.model_sha256")
    sha_at(state["model_config_sha256"], "assets.pocket_bundles.default_windows.state_compatibility_model.model_config_sha256")
    rows = state["clone_languages"]
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("clone_languages must contain exactly English")
    row = object_at(rows[0], "clone_languages[0]", {"language", "cloning_weights_sha256"})
    string_at(row["language"], "clone_languages[0].language", "english")
    sha_at(row["cloning_weights_sha256"], "clone_languages[0].cloning_weights_sha256")


def validate_english_only_catalog(manifest: Path) -> None:
    value = json.loads(manifest.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_names, parse_constant=reject_constant)
    root = object_at(value, "manifest", {"version", "generated", "base_url", "repo", "assets"})
    string_at(root["version"], "manifest.version", "3")
    string_fields(root, "manifest", ("generated", "base_url"))
    string_at(root["base_url"], "manifest.base_url", "https://forgejo.g-grp.com")
    string_at(root["repo"], "manifest.repo", "Max/teammanager-models")
    assets = object_at(root["assets"], "assets", {"pocket_bundles"})
    bundles = object_at(assets["pocket_bundles"], "assets.pocket_bundles", {"version", "release_tag", "description", "default_windows", "language_packs", "optional"})
    string_fields(bundles, "assets.pocket_bundles", ("version", "release_tag", "description"))
    default = object_at(bundles["default_windows"], "assets.pocket_bundles.default_windows", {"platform", "package_version", "package_revision", "model_revision", "default_language", "runtime", "english_model", "catalog_voice", "state_compatibility_model"})
    string_fields(default, "assets.pocket_bundles.default_windows", ("package_version", "package_revision", "model_revision"))
    string_at(default["platform"], "assets.pocket_bundles.default_windows.platform", "windows-amd64-cpu")
    string_at(default["default_language"], "assets.pocket_bundles.default_windows.default_language", "english")
    validate_archive(default["runtime"], "assets.pocket_bundles.default_windows.runtime", "runtime")
    validate_archive(default["english_model"], "assets.pocket_bundles.default_windows.english_model", "model")
    validate_archive(default["catalog_voice"], "assets.pocket_bundles.default_windows.catalog_voice", "voice")
    validate_state_model(default["state_compatibility_model"])
    packs = bundles["language_packs"]
    if not isinstance(packs, list) or len(packs) != 1:
        raise ValueError("language_packs must contain the one required English pack")
    pack = object_at(packs[0], "language_packs[0]", {"archives", "display_name", "group", "id", "kind", "languages"})
    string_at(pack["id"], "language_packs[0].id", "language-english")
    string_at(pack["kind"], "language_packs[0].kind", "language")
    string_at(pack["display_name"], "language_packs[0].display_name", "English")
    string_at(pack["group"], "language_packs[0].group", "individual")
    if pack["languages"] != ["english"]:
        raise ValueError("language_packs[0].languages must contain exactly English")
    if not isinstance(pack["archives"], list) or len(pack["archives"]) != 1:
        raise ValueError("language_packs[0].archives must contain one English model")
    validate_archive(pack["archives"][0], "language_packs[0].archives[0]", "model", optional=True)
    optional = bundles["optional"]
    if not isinstance(optional, list) or len(optional) != 1:
        raise ValueError("optional must contain the required English model")
    validate_archive(optional[0], "optional[0]", "model", optional=True)


def verify(manifest: Path, signature: Path, sha256_sidecar: Path, public_key: Path) -> None:
    if signature.stat().st_size != 64:
        raise ValueError("Ed25519 detached signature must be exactly 64 bytes")
    expected_sidecar = hashlib.sha256(manifest.read_bytes()).hexdigest().encode("ascii") + b"\n"
    if sha256_sidecar.read_bytes() != expected_sidecar:
        raise ValueError("SHA-256 sidecar must be lowercase hexadecimal plus one newline")
    subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key), "-rawin", "-in", str(manifest), "-sigfile", str(signature)], check=True, stdout=subprocess.DEVNULL)
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
