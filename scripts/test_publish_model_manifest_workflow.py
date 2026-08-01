import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".forgejo" / "workflows" / "publish-model-manifest.yml"


class PublishModelManifestWorkflowTests(unittest.TestCase):
    def test_workflow_is_manual_pinned_and_fail_closed(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("@11d5960a326750d5838078e36cf38b85af677262", workflow)
        self.assertIn("${{ forgejo.token }}", workflow)
        self.assertNotIn("secrets.FORGEJO_TOKEN", workflow)
        self.assertIn("MODEL_MANIFEST_SIGNING_KEY_B64", workflow)
        self.assertIn("MODEL_MANIFEST_PUBLIC_KEY_B64", workflow)
        self.assertIn("teammanager-model-manifest-v3-pocket-r3.2", workflow)
        self.assertIn("test \"$release_status\" = 404", workflow)
        self.assertIn("test \"$tag_status\" = 404", workflow)
        self.assertIn('\\"draft\\":true', workflow)
        self.assertIn("\"draft\":false", workflow)
        self.assertIn("trap cleanup EXIT HUP INT TERM", workflow)
        self.assertIn("chmod 0600 \"$private_key\"", workflow)
        self.assertIn("test \"$(wc -c < \"$signature\")\" -eq 64", workflow)
        self.assertIn("test \"$(wc -c < \"$sidecar\")\" -eq 65", workflow)
        self.assertNotIn("set -x", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("actions/upload-artifact", workflow)


if __name__ == "__main__":
    unittest.main()
