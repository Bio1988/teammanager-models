import tempfile
import unittest
from pathlib import Path

import package_managed_radio_transformers as transformers
from package_managed_radio_assets import sha256_file


class TransformerModelRecords(unittest.TestCase):
    def test_pinned_license_inputs_exist_and_notice_has_required_sentence(self):
        for model in transformers.MODELS:
            for archive_name, (source, expected) in model["licenses"].items():
                path = transformers.ROOT / "LICENSES" / source
                self.assertTrue(path.is_file(), archive_name)
                if expected:
                    self.assertEqual(sha256_file(path), expected)
        notice = (transformers.ROOT / "LICENSES" / "NOTICE-Gemma.txt").read_text(encoding="utf-8")
        self.assertIn("Gemma is provided under and subject to the Gemma Terms of Use found at ai.google.dev/gemma/terms", notice)

    def test_build_is_closed_and_rejects_wrong_source(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as out:
            for model in transformers.MODELS:
                (Path(source) / model["gguf"]).write_bytes(b"not the pinned model")
            with self.assertRaises(ValueError):
                transformers.build(source, out)


if __name__ == "__main__":
    unittest.main()
