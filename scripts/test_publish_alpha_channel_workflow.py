import unittest
from pathlib import Path


class AlphaChannelPublisherWorkflowTests(unittest.TestCase):
    def test_manual_publisher_is_custody_gated_and_writes_only_fixed_channel_files(self):
        workflow = (Path(__file__).resolve().parent.parent / ".forgejo/workflows/publish-alpha-channel.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("runs-on: alpha-channel-custody", workflow)
        self.assertIn("expected_source_sha:", workflow)
        self.assertIn("ALPHA_CHANNEL_CUSTODY_RUNNER_ID: ${{ vars.ALPHA_CHANNEL_CUSTODY_RUNNER_ID }}", workflow)
        self.assertNotIn("secrets.ALPHA_CHANNEL_CUSTODY_RUNNER_ID", workflow)
        guard = workflow.index("Fail closed on a custody runner misassignment")
        release_verification = workflow.index("Verify immutable release assets")
        signing = workflow.index("Build sign and verify the fixed Alpha channel")
        self.assertLess(guard, release_verification)
        self.assertLess(guard, signing)
        self.assertIn("the custody boundary", workflow)
        self.assertIn("does not attest that a runner is trustworthy", workflow)
        self.assertIn("ALPHA_CHANNEL_PUBLISH_TOKEN", workflow)
        self.assertIn('raise SystemExit("main must be protected")', workflow)
        self.assertIn('raise SystemExit("main must require approval")', workflow)
        self.assertIn('raise SystemExit("main must require named status contexts")', workflow)
        self.assertIn("MODEL_MANIFEST_SIGNING_KEY_B64", workflow)
        self.assertIn("python3 scripts/alpha_channel.py verify", workflow)
        self.assertIn("git add -- channels/alpha.json channels/alpha.json.sig", workflow)
        self.assertIn("git diff --cached --name-only | grep -Fx 'channels/alpha.json'", workflow)
        self.assertIn("git diff --cached --name-only | grep -Fx 'channels/alpha.json.sig'", workflow)
        for prohibited in ("curl --request POST", "curl -X POST", "forgejo.token", "upload-artifact"):
            self.assertNotIn(prohibited, workflow)
        self.assertNotIn("git tag", workflow)


if __name__ == "__main__":
    unittest.main()
