import unittest
from pathlib import Path


class SigningWorkflowTests(unittest.TestCase):
    def test_manual_candidate_signing_is_preflighted_and_never_publishes(self):
        workflow = (Path(__file__).resolve().parent.parent / ".forgejo/workflows/sign-model-manifest-candidate.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("expected_source_sha:", workflow)
        preflight = workflow.index("Preflight reviewed protected main")
        checkout = workflow.index("Check out the preflighted trusted main")
        signing = workflow.index("Sign and locally verify immutable candidate assets")
        evidence = workflow.index("Retain signed candidate evidence")
        self.assertLess(preflight, checkout)
        self.assertLess(checkout, signing)
        self.assertLess(signing, evidence)
        self.assertIn('test "${GITHUB_REF:-}" = refs/heads/main', workflow)
        self.assertIn("ref: ${{ forgejo.sha }}", workflow)
        self.assertNotIn("ref: ${{ inputs.expected_source_sha }}", workflow)
        self.assertIn("branch.get(\"protected\") is True", workflow)
        self.assertIn("branch[\"required_approvals\"] >= 1", workflow)
        self.assertIn("branch.get(\"enable_status_check\") is True", workflow)
        self.assertIn("status.get(\"state\") == \"success\"", workflow)
        self.assertIn("MODEL_MANIFEST_SIGNING_KEY_B64: ${{ secrets.MODEL_MANIFEST_SIGNING_KEY_B64 }}", workflow)
        self.assertLess(preflight, workflow.index("MODEL_MANIFEST_SIGNING_KEY_B64"))
        self.assertIn("unset FORGEJO_TOKEN GITEA_TOKEN GITHUB_TOKEN", workflow)
        self.assertIn("unset MODEL_MANIFEST_SIGNING_KEY_B64", workflow)
        self.assertIn("signature_verified", workflow)
        self.assertIn('"status": "not-attempted"', workflow)
        for prohibited in ("forgejo.token", "/releases", "/tags", "curl --request POST", "curl -X POST"):
            self.assertNotIn(prohibited, workflow)


if __name__ == "__main__":
    unittest.main()
