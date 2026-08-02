import unittest
from pathlib import Path


class AlphaChannelPublisherWorkflowTests(unittest.TestCase):
    def test_publisher_reuses_only_the_existing_alpha_contract_and_application_key(self):
        workflow = (Path(__file__).resolve().parent.parent / ".forgejo/workflows/publish-alpha-channel.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("runs-on: alpha-channel-custody", workflow)
        self.assertIn("ALPHA_CHANNEL_CUSTODY_RUNNER_ID: ${{ vars.ALPHA_CHANNEL_CUSTODY_RUNNER_ID }}", workflow)
        self.assertIn("the custody boundary", workflow)
        self.assertIn("does not attest that a runner is trustworthy", workflow)
        self.assertIn("ALPHA_CHANNEL_SIGNING_KEY_B64", workflow)
        self.assertIn("ALPHA_CHANNEL_PUBLIC_KEY_B64", workflow)
        self.assertNotIn("MODEL_MANIFEST_SIGNING_KEY_B64", workflow)
        self.assertNotIn("MODEL_MANIFEST_PUBLIC_KEY_B64", workflow)
        self.assertIn("go run ./cmd/alpha-channel publish", workflow)
        self.assertIn("go run ./cmd/alpha-channel verify", workflow)
        self.assertIn("go run ./cmd/alpha-channel verify-candidate", workflow)
        self.assertIn('"key_id": "alpha-1"', workflow)
        for field in ("release_sequence", "race_commit", "relay_commit", "authenticode_policy", "platform", "architecture"):
            self.assertIn(field, workflow)
        self.assertIn("branch.get(\"protected\") is not True", workflow)
        self.assertIn("git add -- channels/alpha.json channels/alpha.json.sig", workflow)
        for prohibited in ("git tag", "upload-artifact", "curl --request POST", "curl -X POST"):
            self.assertNotIn(prohibited, workflow)


if __name__ == "__main__":
    unittest.main()
