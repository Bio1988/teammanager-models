#!/usr/bin/env python3
"""Create and validate non-publication evidence for one signing run."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


REPOSITORY = "Max/teammanager-models"
REF = "refs/heads/main"
SHA = re.compile(r"[0-9a-f]{40}\Z")
ASSETS = ("teammanager-model-manifest-v3.json", "teammanager-model-manifest-v3.json.sig", "teammanager-model-manifest-v3.json.sha256")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def run_url(repository: str, number: str, server_url: str) -> str:
    return f"{server_url.rstrip('/')}/{repository}/actions/runs/{number}"


def evidence(output: Path, source_sha: str, repository: str, ref: str, run_id: str, run_number: str, run_attempt: str, server_url: str) -> dict[str, object]:
    require(repository == REPOSITORY, "candidate repository is not canonical")
    require(ref == REF, "candidate ref is not canonical main")
    require(SHA.fullmatch(source_sha) is not None, "candidate source SHA is invalid")
    require(all(value.isdecimal() and int(value) > 0 for value in (run_id, run_number, run_attempt)), "candidate run identity is invalid")
    assets = []
    for name in ASSETS:
        path = output / name
        require(path.is_file(), f"missing candidate asset: {name}")
        assets.append({"name": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size})
    return {"contract": "teammanager-model-manifest-v3-pocket-r3.2", "repository": repository, "ref": ref, "source_sha": source_sha, "run": {"id": run_id, "number": run_number, "attempt": run_attempt, "url": run_url(repository, run_number, server_url)}, "assets": assets, "signature_verified": True, "publication": {"status": "not-attempted", "reason": "This workflow has no tag, release, or repository-write step; external signing-custody authorization is required before publication."}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-number", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--server-url", required=True)
    args = parser.parse_args()
    (args.output / "candidate-evidence.json").write_text(json.dumps(evidence(args.output, args.source_sha, args.repository, args.ref, args.run_id, args.run_number, args.run_attempt, args.server_url), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
