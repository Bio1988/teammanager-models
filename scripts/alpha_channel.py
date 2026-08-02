#!/usr/bin/env python3
"""Build and fail-closed validate the fixed TeamManager Alpha update channel."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from verify_release_manifest import reject_constant, reject_duplicate_names, verify_detached_ed25519

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
RELEASE_URL = re.compile(
    r"https://forgejo\.g-grp\.com/Max/([a-z0-9-]+)/releases/download/([^/]+)/([^/?#]+)\Z"
)
COMPONENTS = {
    "race-engineer-go": "race-engineer-go",
    "teammanager-relay": "teammanager-relay",
}


def require_string(value: object, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where} must be a non-empty string")
    return value


def require_positive_int(value: object, where: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{where} must be a positive integer")
    return value


def require_sha256(value: object, where: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise ValueError(f"{where} must be lowercase SHA-256")
    return value


def validate_asset(value: object, index: int) -> None:
    where = f"assets[{index}]"
    if not isinstance(value, dict) or set(value) != {"component", "version", "release_tag", "asset_name", "url", "size_bytes", "sha256"}:
        raise ValueError(f"{where} has an invalid schema")
    component = require_string(value["component"], f"{where}.component")
    expected_repo = COMPONENTS.get(component)
    if expected_repo is None:
        raise ValueError(f"{where}.component is not an Alpha component")
    version = require_string(value["version"], f"{where}.version")
    tag = require_string(value["release_tag"], f"{where}.release_tag")
    name = require_string(value["asset_name"], f"{where}.asset_name")
    url = require_string(value["url"], f"{where}.url")
    if urlparse(url).query or urlparse(url).fragment:
        raise ValueError(f"{where}.url must not carry a query or fragment")
    match = RELEASE_URL.fullmatch(url)
    if match is None or match.group(1) != expected_repo or match.group(2) != tag or match.group(3) != name:
        raise ValueError(f"{where}.url must be the exact canonical immutable Forgejo release asset URL")
    if "/" in name or name in {".", ".."}:
        raise ValueError(f"{where}.asset_name must be a file name")
    if version != tag:
        raise ValueError(f"{where}.version must equal its immutable release tag")
    require_positive_int(value["size_bytes"], f"{where}.size_bytes")
    require_sha256(value["sha256"], f"{where}.sha256")


def validate(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"version", "channel", "generated_at", "assets"}:
        raise ValueError("channel has an invalid schema")
    if value["version"] != "1" or value["channel"] != "alpha":
        raise ValueError("channel version and name must be the fixed Alpha contract")
    generated = require_string(value["generated_at"], "channel.generated_at")
    if not generated.endswith("Z"):
        raise ValueError("channel.generated_at must be UTC RFC3339")
    try:
        datetime.fromisoformat(generated.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise ValueError("channel.generated_at must be UTC RFC3339") from error
    assets = value["assets"]
    if not isinstance(assets, list) or len(assets) != len(COMPONENTS):
        raise ValueError("channel must contain exactly the two Alpha assets")
    for index, asset in enumerate(assets):
        validate_asset(asset, index)
    if [asset["component"] for asset in assets] != list(COMPONENTS):
        raise ValueError("channel assets must be race-engineer-go then teammanager-relay")


def load_and_validate(channel: Path) -> None:
    value = json.loads(channel.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_names, parse_constant=reject_constant)
    validate(value)


def build(args: argparse.Namespace) -> None:
    assets = []
    for component in COMPONENTS:
        prefix = component.replace("-", "_")
        tag = getattr(args, f"{prefix}_release_tag")
        name = getattr(args, f"{prefix}_asset_name")
        assets.append({
            "component": component,
            "version": tag,
            "release_tag": tag,
            "asset_name": name,
            "url": f"https://forgejo.g-grp.com/Max/{COMPONENTS[component]}/releases/download/{tag}/{name}",
            "size_bytes": int(getattr(args, f"{prefix}_size_bytes")),
            "sha256": getattr(args, f"{prefix}_sha256"),
        })
    value = {"version": "1", "channel": "alpha", "generated_at": args.generated_at, "assets": assets}
    validate(value)
    args.output.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--generated-at", required=True)
    for component in COMPONENTS:
        prefix = component.replace("-", "_")
        build_parser.add_argument(f"--{prefix.replace('_', '-')}-release-tag", required=True)
        build_parser.add_argument(f"--{prefix.replace('_', '-')}-asset-name", required=True)
        build_parser.add_argument(f"--{prefix.replace('_', '-')}-size-bytes", required=True)
        build_parser.add_argument(f"--{prefix.replace('_', '-')}-sha256", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--channel", type=Path, required=True)
    verify_parser.add_argument("--signature", type=Path, required=True)
    verify_parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        build(args)
    else:
        load_and_validate(args.channel)
        verify_detached_ed25519(args.channel, args.signature, args.public_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
