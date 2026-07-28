import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ManifestCatalogTests(unittest.TestCase):
    def test_source_manifest_is_a_versioned_catalog_without_release_sidecars(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

        self.assertIsInstance(manifest.get("version"), str)
        self.assertIsInstance(manifest.get("assets"), dict)
        self.assertIn("models", manifest["assets"])
        self.assertIn("pocket_bundles", manifest["assets"])
        self.assertFalse((ROOT / "manifest.json.sig").exists())
        self.assertFalse((ROOT / "manifest.json.sha256").exists())


if __name__ == "__main__":
    unittest.main()
