import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ManifestCatalogTests(unittest.TestCase):
    def test_source_manifest_is_a_versioned_catalog_without_release_sidecars(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

        self.assertIsInstance(manifest.get("version"), str)
        self.assertIsInstance(manifest.get("assets"), dict)
        self.assertEqual(set(manifest["assets"]), {"pocket_bundles"})
        self.assertIn("pocket_bundles", manifest["assets"])
        self.assertIn("state_compatibility_model", manifest["assets"]["pocket_bundles"]["default_windows"])
        self.assertNotIn("checksums", manifest)
        self.assertFalse((ROOT / "manifest.json.sig").exists())
        self.assertFalse((ROOT / "manifest.json.sha256").exists())

    def test_alpha_catalog_advertises_and_defaults_english_only(self):
        bundles = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["assets"]["pocket_bundles"]
        default_windows = bundles["default_windows"]

        self.assertEqual(default_windows["default_language"], "english")
        self.assertTrue(default_windows["english_model"]["default"])
        self.assertEqual(default_windows["english_model"]["layout"]["language"], "english")
        self.assertEqual(
            [entry["language"] for entry in default_windows["state_compatibility_model"]["clone_languages"]],
            ["english"],
        )
        self.assertEqual([pack["languages"] for pack in bundles["language_packs"]], [["english"]])

        advertised_archives = [archive for pack in bundles["language_packs"] for archive in pack["archives"]]
        downloadable_archives = advertised_archives + bundles["optional"]
        self.assertTrue(downloadable_archives)
        self.assertTrue(all(archive["layout"]["language"] == "english" for archive in downloadable_archives))


if __name__ == "__main__":
    unittest.main()
