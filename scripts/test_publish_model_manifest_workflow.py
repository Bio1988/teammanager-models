import importlib.util
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("release_protocol.py")
SPEC = importlib.util.spec_from_file_location("release_protocol", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "a" * 40


class FakeApi:
    def __init__(self, branch=None, status=None):
        self.branch = branch or {"protected": True, "required_approvals": 1, "enable_status_check": True,
                               "status_check_contexts": ["verify"], "commit": {"id": SHA}}
        self.commit_status = status or {"state": "success", "statuses": [{"context": "verify", "status": "success"}]}
        self.calls, self.tag, self.release = [], None, None

    def request(self, method, path, body=None, accept="application/json"):
        self.calls.append((method, path, body, accept))
        if method == "GET" and path.endswith(f"releases/tags/{module.TAG}"):
            if self.release is None:
                raise urllib.error.HTTPError(path, 404, "missing", {}, None)
        if method == "GET" and path.endswith(f"tags/{module.TAG}"):
            if self.tag is None:
                raise urllib.error.HTTPError(path, 404, "missing", {}, None)
        if method == "DELETE" and path.endswith(f"tags/{module.TAG}"):
            self.tag = None
        return b"{}"

    def json(self, method, path, body=None):
        self.calls.append((method, path, body, "json"))
        if path.endswith("/branches/main"):
            return self.branch
        if path.endswith(f"/commits/{SHA}/status"):
            return self.commit_status
        if path.endswith(f"tags/{module.TAG}"):
            return {"commit": {"id": self.tag}}
        if method == "POST" and path.endswith("/tags"):
            self.tag = body["target"]
            return {}
        if method == "POST" and path.endswith("/releases"):
            self.release = {"id": 9, "draft": True, "tag_name": module.TAG, "target_commitish": body["target_commitish"]}
            return self.release
        if method == "GET" and path.endswith("/releases/9"):
            return self.release
        if method == "PATCH" and path.endswith("/releases/9"):
            self.release["draft"] = body["draft"]
            return self.release
        raise AssertionError((method, path, body))


class ReleaseProtocolTests(unittest.TestCase):
    def test_untrusted_dispatch_cannot_run_checkout_code_or_receive_signing_env_before_preflight(self):
        workflow = (Path(__file__).resolve().parent.parent / ".forgejo/workflows/publish-model-manifest.yml").read_text(encoding="utf-8")
        preflight = workflow.index("Preflight reviewed protected main")
        checkout = workflow.index("Check out the preflighted trusted main")
        signing = workflow.index("MODEL_MANIFEST_SIGNING_KEY_B64")
        self.assertLess(preflight, checkout)
        self.assertLess(checkout, signing)
        self.assertIn("ref: ${{ forgejo.sha }}", workflow)
        self.assertNotIn("ref: ${{ inputs.expected_source_sha }}", workflow)
        self.assertIn('test "${GITHUB_REF:-}" = refs/heads/main', workflow)

    def test_preflight_requires_protected_approved_successful_current_main(self):
        api = FakeApi()
        module.preflight(api, "Max/teammanager-models", SHA, SHA)
        self.assertEqual([call[1] for call in api.calls], [
            "/repos/Max/teammanager-models/branches/main",
            f"/repos/Max/teammanager-models/commits/{SHA}/status",
        ])
        for key, value in (("protected", False), ("required_approvals", 0), ("enable_status_check", False)):
            branch = dict(api.branch)
            branch[key] = value
            with self.assertRaises(RuntimeError):
                module.preflight(FakeApi(branch=branch), "Max/teammanager-models", SHA, SHA)
        with self.assertRaises(RuntimeError):
            module.preflight(api, "Max/teammanager-models", "A" * 40, SHA)

    def test_reserve_rejects_replay_and_cleans_only_its_new_tag_if_draft_creation_fails(self):
        api = FakeApi()
        release_id = module.reserve(api, "Max/teammanager-models", SHA)
        self.assertEqual(release_id, 9)
        self.assertEqual(api.tag, SHA)
        with self.assertRaises(RuntimeError):
            module.reserve(api, "Max/teammanager-models", SHA)

        class DraftFailure(FakeApi):
            def json(self, method, path, body=None):
                if method == "POST" and path.endswith("/releases"):
                    raise RuntimeError("draft failed")
                return super().json(method, path, body)

        failing = DraftFailure()
        with self.assertRaisesRegex(RuntimeError, "draft failed"):
            module.reserve(failing, "Max/teammanager-models", SHA)
        self.assertIsNone(failing.tag)
        self.assertIn(("DELETE", f"/repos/Max/teammanager-models/tags/{module.TAG}", None, "application/json"), failing.calls)

        class WrongTag(FakeApi):
            def json(self, method, path, body=None):
                value = super().json(method, path, body)
                if method == "POST" and path.endswith("/tags"):
                    self.tag = "b" * 40
                return value

        with self.assertRaisesRegex(RuntimeError, "reserved tag"):
            module.reserve(WrongTag(), "Max/teammanager-models", SHA)

    def test_draft_metadata_rejects_duplicate_assets_and_size_mismatch(self):
        class AssetApi:
            def __init__(self, rows): self.rows = rows
            def json(self, *_): return self.rows
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            for name in module.ASSETS:
                (output / name).write_bytes(b"x")
            duplicate = [{"name": module.ASSETS[0], "id": 1, "size": 1}] * 3
            with self.assertRaisesRegex(RuntimeError, "exactly three"):
                module.assets(AssetApi(duplicate), "Max/teammanager-models", 9, output)
            rows = [{"name": name, "id": index, "size": 2} for index, name in enumerate(module.ASSETS, 1)]
            with self.assertRaisesRegex(RuntimeError, "size"):
                module.assets(AssetApi(rows), "Max/teammanager-models", 9, output)

    def test_publish_response_loss_or_public_failure_best_effort_redrafts(self):
        api = FakeApi()
        api.release = {"id": 9, "draft": True, "tag_name": module.TAG, "target_commitish": SHA}
        original = module.reserve, module.upload, module.assets, module.tag_sha, module.verify_public_downloads
        calls = []
        try:
            module.reserve = lambda *_: 9
            module.upload = lambda *_: calls.append("upload")
            module.assets = lambda *_: {name: number for number, name in enumerate(module.ASSETS, 1)}
            module.tag_sha = lambda *_: SHA
            def downloads(*_):
                calls.append("public")
                raise RuntimeError("public download failed")
            module.verify_public_downloads = downloads
            with self.assertRaisesRegex(RuntimeError, "public download failed"):
                module.publish(api, "Max/teammanager-models", "https://forgejo.example", SHA, Path("out"), Path("source"), Path("pub"))
        finally:
            module.reserve, module.upload, module.assets, module.tag_sha, module.verify_public_downloads = original
        self.assertEqual(calls, ["upload", "public"])
        self.assertTrue(any(call[0] == "PATCH" and call[2] == {"draft": False} for call in api.calls))
        self.assertTrue(any(call[0] == "PATCH" and call[2] == {"draft": True} for call in api.calls))

    def test_final_tag_mutation_redrafts_after_public_verification(self):
        api = FakeApi()
        api.release = {"id": 9, "draft": True, "tag_name": module.TAG, "target_commitish": SHA}
        original = module.reserve, module.upload, module.assets, module.tag_sha, module.verify_public_downloads
        try:
            module.reserve = lambda *_: 9
            module.upload = lambda *_: None
            module.assets = lambda *_: {name: number for number, name in enumerate(module.ASSETS, 1)}
            values = iter([SHA, "b" * 40])
            module.tag_sha = lambda *_: next(values)
            module.verify_public_downloads = lambda *_: None
            with self.assertRaisesRegex(RuntimeError, "tag changed after"):
                module.publish(api, "Max/teammanager-models", "https://forgejo.example", SHA, Path("out"), Path("source"), Path("pub"))
        finally:
            module.reserve, module.upload, module.assets, module.tag_sha, module.verify_public_downloads = original
        self.assertTrue(any(call[0] == "PATCH" and call[2] == {"draft": True} for call in api.calls))

    def test_command_fails_before_api_use_when_automatic_token_is_absent(self):
        with mock.patch.dict(os.environ, {"FORGEJO_TOKEN": ""}, clear=False), \
             mock.patch.object(sys, "argv", ["release_protocol.py", "preflight", "--api", "https://forgejo.example/api/v1", "--repository", "Max/teammanager-models", "--expected-sha", SHA, "--checkout-sha", SHA]):
            with self.assertRaisesRegex(RuntimeError, "FORGEJO_TOKEN"):
                module.main()


if __name__ == "__main__":
    unittest.main()
