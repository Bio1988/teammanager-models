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
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn('CANONICAL_REPOSITORY: Max/teammanager-models', workflow)
        self.assertIn('CANONICAL_REF: refs/heads/main', workflow)
        self.assertIn('CANONICAL_ORIGIN: https://forgejo.g-grp.com', workflow)
        self.assertIn('test "${FORGEJO_REPOSITORY:-}" = "$CANONICAL_REPOSITORY"', workflow)
        self.assertIn('test "${FORGEJO_REF:-}" = "$CANONICAL_REF"', workflow)
        self.assertIn('test "${FORGEJO_SERVER_URL:-}" = "$CANONICAL_ORIGIN"', workflow)
        self.assertIn('test "${FORGEJO_API_URL:-}" = "$CANONICAL_ORIGIN/api/v1"', workflow)
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
        self.assertIn("scripts/candidate_evidence.py", workflow)
        self.assertIn("actions/runs/${{ forgejo.run_number }}", workflow)
        self.assertIn('RUN_URL: https://forgejo.g-grp.com/Max/teammanager-models/actions/runs/${{ forgejo.run_number }}', workflow)
        self.assertIn("candidate-run-${{ forgejo.run_number }}-attempt-${{ forgejo.run_attempt }}-sha-${{ inputs.expected_source_sha }}", workflow)
        self.assertIn("retention-days: 7", workflow)
        self.assertIn("uses: https://code.forgejo.org/forgejo/upload-artifact@16871d9e8cfcf27ff31822cac382bbb5450f1e1e", workflow)
        self.assertNotIn("uses: https://data.forgejo.org/actions/upload-artifact@", workflow)
        for prohibited in ("forgejo.token", "/releases", "/tags", "curl --request POST", "curl -X POST"):
            self.assertNotIn(prohibited, workflow)

    def test_evidence_provenance_cannot_be_omitted_or_retargeted(self):
        workflow = (Path(__file__).resolve().parent.parent / ".forgejo/workflows/sign-model-manifest-candidate.yml").read_text(encoding="utf-8")
        evidence = workflow
        required = ("Max/teammanager-models", "refs/heads/main", "RUN_ID", "RUN_NUMBER", "RUN_ATTEMPT", "RUN_URL")
        for value in required:
            self.assertIn(value, evidence)
        self.assertNotIn('"publication": {"status": "published"', evidence)


if __name__ == "__main__":
    unittest.main()
