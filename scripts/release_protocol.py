#!/usr/bin/env python3
"""Fail-closed Forgejo release protocol for the model-manifest publisher."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from verify_release_manifest import verify


ASSETS = ("teammanager-model-manifest-v3.json", "teammanager-model-manifest-v3.json.sig", "teammanager-model-manifest-v3.json.sha256")
TAG = "teammanager-model-manifest-v3-pocket-r3.2"
SHA = re.compile(r"[0-9a-f]{40}\Z")


class Api:
    def __init__(self, api: str, token: str):
        self.api, self.token = api.rstrip("/"), token

    def request(self, method: str, path: str, body: object | None = None, accept: str = "application/json") -> bytes:
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        request = urllib.request.Request(self.api + path, data=data, method=method, headers={
            "Authorization": f"token {self.token}", "Accept": accept,
            **({"Content-Type": "application/json"} if data is not None else {}),
        })
        with urllib.request.urlopen(request) as response:
            return response.read()

    def json(self, method: str, path: str, body: object | None = None) -> object:
        return json.loads(self.request(method, path, body))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def preflight(api: Api, repo: str, expected: str, checkout: str) -> None:
    require(bool(SHA.fullmatch(expected)), "expected_source_sha must be 40 lowercase hexadecimal characters")
    require(checkout == expected, "checked-out commit does not equal expected_source_sha")
    branch = api.json("GET", f"/repos/{repo}/branches/main")
    require(isinstance(branch, dict), "invalid branch response")
    require(branch.get("protected") is True, "main must be protected")
    require(isinstance(branch.get("required_approvals"), int) and branch["required_approvals"] > 0, "main must require PR approvals")
    contexts = branch.get("status_check_contexts")
    require(branch.get("enable_status_check") is True and isinstance(contexts, list) and contexts, "main must require status checks")
    require(branch.get("commit", {}).get("id") == expected, "expected_source_sha is not current main")
    status = api.json("GET", f"/repos/{repo}/commits/{expected}/status")
    require(isinstance(status, dict) and status.get("state") == "success", "expected_source_sha has no successful combined status")
    latest = {row.get("context"): row.get("status") for row in status.get("statuses", []) if isinstance(row, dict)}
    require(all(latest.get(context) == "success" for context in contexts), "a required status check is not successful")


def status(api: Api, path: str) -> int:
    try:
        api.request("GET", path)
    except urllib.error.HTTPError as error:
        return error.code
    return 200


def tag_sha(api: Api, repo: str) -> str:
    value = api.json("GET", f"/repos/{repo}/git/refs/tags/{TAG}")
    try:
        return value["object"]["sha"]
    except (KeyError, TypeError):
        raise RuntimeError("invalid tag response") from None


def reserve(api: Api, repo: str, expected: str) -> int:
    require(status(api, f"/repos/{repo}/releases/tags/{TAG}") == 404, "release tag already exists")
    require(status(api, f"/repos/{repo}/git/refs/tags/{TAG}") == 404, "git tag already exists")
    tag_created = False
    try:
        api.json("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/tags/{TAG}", "sha": expected})
        tag_created = True
        require(tag_sha(api, repo) == expected, "reserved tag does not target expected_source_sha")
        release = api.json("POST", f"/repos/{repo}/releases", {"tag_name": TAG, "target_commitish": expected, "name": "TeamManager model manifest v3 Pocket R3.2", "draft": True})
    except Exception:
        if tag_created and tag_sha(api, repo) == expected:
            api.request("DELETE", f"/repos/{repo}/git/refs/tags/{TAG}")
        raise
    try:
        release_id = release["id"]
    except (KeyError, TypeError):
        raise RuntimeError("invalid draft release response") from None
    require(isinstance(release_id, int) and release_id > 0, "draft release id must be numeric")
    return release_id


def upload(api: Api, repo: str, release_id: int, output: Path) -> None:
    # urllib's standard library has no safe compact multipart helper; curl never logs the token without -v.
    for name in ASSETS:
        path = output / name
        require(path.is_file(), f"missing release asset: {name}")
        import subprocess
        subprocess.run(["curl", "--fail", "--silent", "--show-error", "--request", "POST", "--header", f"Authorization: token {api.token}", "--form", f"attachment=@{path};filename={name}", f"{api.api}/repos/{repo}/releases/{release_id}/assets?name={urllib.parse.quote(name)}"], check=True)


def assets(api: Api, repo: str, release_id: int) -> dict[str, int]:
    rows = api.json("GET", f"/repos/{repo}/releases/{release_id}/assets")
    require(isinstance(rows, list), "invalid release assets response")
    result = {row.get("name"): row.get("id") for row in rows if isinstance(row, dict)}
    require(set(result) == set(ASSETS) and all(isinstance(value, int) and value > 0 for value in result.values()), "release must contain exactly three unique named assets")
    return result


def verify_downloads(api: Api, repo: str, release_id: int, asset_ids: dict[str, int], output: Path, source: Path, public_key: Path, server: str | None = None) -> None:
    with tempfile.TemporaryDirectory() as temp:
        downloaded = Path(temp)
        for name, asset_id in asset_ids.items():
            if server is None:
                data = api.request("GET", f"/repos/{repo}/releases/assets/{asset_id}", accept="application/octet-stream")
            else:
                request = urllib.request.Request(f"{server.rstrip('/')}/{repo}/releases/download/{TAG}/{name}")
                with urllib.request.urlopen(request) as response:
                    data = response.read()
            (downloaded / name).write_bytes(data)
            require((downloaded / name).read_bytes() == (output / name).read_bytes(), f"downloaded asset differs: {name}")
        require((downloaded / ASSETS[0]).read_bytes() == source.read_bytes(), "downloaded manifest differs from source")
        verify(downloaded / ASSETS[0], downloaded / ASSETS[1], downloaded / ASSETS[2], public_key)


def publish(api: Api, repo: str, server: str, expected: str, output: Path, source: Path, public_key: Path) -> None:
    release_id = reserve(api, repo, expected)
    upload(api, repo, release_id, output)
    asset_ids = assets(api, repo, release_id)
    require(tag_sha(api, repo) == expected, "tag changed before draft verification")
    verify_downloads(api, repo, release_id, asset_ids, output, source, public_key)
    draft = api.json("GET", f"/repos/{repo}/releases/{release_id}")
    require(draft.get("draft") is True and draft.get("tag_name") == TAG and draft.get("target_commitish") == expected, "draft release changed before publish")
    api.json("PATCH", f"/repos/{repo}/releases/{release_id}", {"draft": False})
    try:
        verify_downloads(api, repo, release_id, asset_ids, output, source, public_key, server)
    except Exception:
        api.json("PATCH", f"/repos/{repo}/releases/{release_id}", {"draft": True})
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("preflight", "publish"):
        item = sub.add_parser(command)
        item.add_argument("--api", required=True)
        item.add_argument("--repository", required=True)
        item.add_argument("--expected-sha", required=True)
    pre = sub.choices["preflight"]
    pre.add_argument("--checkout-sha", required=True)
    pub = sub.choices["publish"]
    pub.add_argument("--server", required=True)
    pub.add_argument("--output", type=Path, required=True)
    pub.add_argument("--source-manifest", type=Path, required=True)
    pub.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("FORGEJO_TOKEN", "")
    require(bool(token), "FORGEJO_TOKEN is required")
    client = Api(args.api, token)
    if args.command == "preflight":
        preflight(client, args.repository, args.expected_sha, args.checkout_sha)
    else:
        publish(client, args.repository, args.server, args.expected_sha, args.output, args.source_manifest, args.public_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
