import copy
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
CATALOG = json.loads((Path(__file__).resolve().parent.parent / "manifest.json").read_text(encoding="utf-8"))


class ReleaseManifestVerifierTests(unittest.TestCase):
    def write_catalog(self, root: Path, catalog=None) -> Path:
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(CATALOG if catalog is None else catalog), encoding="utf-8")
        return manifest

    def test_accepts_current_closed_r32_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            module.validate_english_only_catalog(self.write_catalog(Path(temp)))

    def test_rejects_unknown_members_and_type_confusion_at_every_contract_layer(self):
        cases = []
        unknown_root = copy.deepcopy(CATALOG); unknown_root["surprise"] = True; cases.append(unknown_root)
        unknown_archive = copy.deepcopy(CATALOG); unknown_archive["assets"]["pocket_bundles"]["default_windows"]["runtime"]["surprise"] = True; cases.append(unknown_archive)
        string_size = copy.deepcopy(CATALOG); string_size["assets"]["pocket_bundles"]["default_windows"]["runtime"]["size_bytes"] = "306398674"; cases.append(string_size)
        bool_size = copy.deepcopy(CATALOG); bool_size["assets"]["pocket_bundles"]["default_windows"]["runtime"]["size_bytes"] = True; cases.append(bool_size)
        unknown_layout = copy.deepcopy(CATALOG); unknown_layout["assets"]["pocket_bundles"]["default_windows"]["runtime"]["layout"]["extra"] = "no"; cases.append(unknown_layout)
        unknown_state = copy.deepcopy(CATALOG); unknown_state["assets"]["pocket_bundles"]["default_windows"]["state_compatibility_model"]["extra"] = "no"; cases.append(unknown_state)
        unknown_pack = copy.deepcopy(CATALOG); unknown_pack["assets"]["pocket_bundles"]["language_packs"][0]["extra"] = "no"; cases.append(unknown_pack)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, catalog in enumerate(cases):
                with self.subTest(index=index):
                    with self.assertRaises(ValueError):
                        module.validate_english_only_catalog(self.write_catalog(root, catalog))

    def test_requires_the_exact_english_default_clone_and_language_pack_contract(self):
        cases = []
        no_pack = copy.deepcopy(CATALOG); no_pack["assets"]["pocket_bundles"]["language_packs"] = []; cases.append(no_pack)
        german_pack = copy.deepcopy(CATALOG); german_pack["assets"]["pocket_bundles"]["language_packs"][0]["languages"] = ["german"]; cases.append(german_pack)
        german_clone = copy.deepcopy(CATALOG); german_clone["assets"]["pocket_bundles"]["default_windows"]["state_compatibility_model"]["clone_languages"][0]["language"] = "german"; cases.append(german_clone)
        wrong_optional = copy.deepcopy(CATALOG); wrong_optional["assets"]["pocket_bundles"]["optional"][0]["optional"] = False; cases.append(wrong_optional)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, catalog in enumerate(cases):
                with self.subTest(index=index):
                    with self.assertRaises(ValueError):
                        module.validate_english_only_catalog(self.write_catalog(root, catalog))

    def test_rejects_duplicates_and_non_standard_json_constants(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "manifest.json"
            manifest.write_text('{"version":"3","version":"3"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                module.validate_english_only_catalog(manifest)
            manifest.write_text('{"version":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid JSON constant"):
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
