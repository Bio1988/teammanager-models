import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_release_manifest.py")
SPEC = importlib.util.spec_from_file_location("verify_release_manifest", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ReleaseManifestVerifierTests(unittest.TestCase):
    def write_catalog(self, root: Path) -> Path:
        catalog = {
            "assets": {"pocket_bundles": {"default_windows": {
                "default_language": "english",
                "english_model": {"layout": {"language": "english"}},
                "state_compatibility_model": {"clone_languages": [{"language": "english"}]},
            }, "language_packs": [{"languages": ["english"], "archives": [
                {"layout": {"language": "english"}},
            ]}], "optional": [{"layout": {"language": "english"}}]}}}
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(catalog), encoding="utf-8")
        return manifest

    def test_accepts_exactly_english_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            module.validate_english_only_catalog(self.write_catalog(Path(temp)))

    def test_rejects_non_english_catalog_and_duplicate_members(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.write_catalog(root)
            catalog = json.loads(manifest.read_text(encoding="utf-8"))
            catalog["assets"]["pocket_bundles"]["optional"][0]["layout"]["language"] = "german"
            manifest.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "English"):
                module.validate_english_only_catalog(manifest)
            manifest.write_text('{"assets":{},"assets":{}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                module.validate_english_only_catalog(manifest)

    def test_requires_lowercase_hash_and_one_newline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.write_catalog(root)
            sidecar = root / "manifest.json.sha256"
            sidecar.write_bytes(hashlib.sha256(manifest.read_bytes()).hexdigest().encode("ascii") + b"\n")
            self.assertEqual(sidecar.stat().st_size, 65)
            sidecar.write_bytes(sidecar.read_bytes().upper())
            (root / "signature.sig").write_bytes(b"x" * 64)
            with self.assertRaisesRegex(ValueError, "sidecar"):
                module.verify(manifest, root / "signature.sig", sidecar, root / "missing.pub")


if __name__ == "__main__":
    unittest.main()
