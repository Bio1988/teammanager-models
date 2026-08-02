import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("candidate_evidence.py")
SPEC = importlib.util.spec_from_file_location("candidate_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CandidateEvidenceTests(unittest.TestCase):
    def output(self, root):
        for name in module.ASSETS:
            (root / name).write_bytes(name.encode())

    def test_binds_canonical_source_and_exact_run_url(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp); self.output(output)
            value = module.evidence(output, "a" * 40, module.REPOSITORY, module.REF, "42", "7", "1", "https://forgejo.g-grp.com/")
            self.assertEqual(value["run"]["url"], "https://forgejo.g-grp.com/Max/teammanager-models/actions/runs/7")
            self.assertEqual([asset["name"] for asset in value["assets"]], list(module.ASSETS))

    def test_rejects_missing_or_wrong_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp); self.output(output)
            cases = (("", module.REPOSITORY, module.REF, "1", "2", "1"), ("a" * 40, "other/repo", module.REF, "1", "2", "1"), ("a" * 40, module.REPOSITORY, "refs/heads/other", "1", "2", "1"), ("a" * 40, module.REPOSITORY, module.REF, "", "2", "1"), ("a" * 40, module.REPOSITORY, module.REF, "1", "bad", "1"))
            for case in cases:
                with self.subTest(case=case):
                    with self.assertRaises(ValueError):
                        module.evidence(output, *case, "https://forgejo.g-grp.com")


if __name__ == "__main__":
    unittest.main()
