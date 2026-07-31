import copy
import json
import re
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
V4_CANDIDATE = ROOT / "manifest-v4.candidate.json"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
POCKET_DEFAULTS = {
    "teammanager__pocket-runtime-win-cpu",
    "kyutai__pocket-tts-english-model",
    "kyutai__pocket-voice-alba",
}
POCKET_LANGUAGES = {
    "pocket-language-english",
    "pocket-language-german",
    "pocket-language-italian",
    "pocket-language-portuguese",
    "pocket-language-spanish",
    "pocket-language-french_24l",
    "pocket-language-german_24l",
    "pocket-language-italian_24l",
    "pocket-language-portuguese_24l",
    "pocket-language-spanish_24l",
}
WHISPER = {
    "whispercpp-runtime-windows-amd64-1.9.1",
    "whisper-base-q5_1",
    "whisper-small-q5_1",
}


def object_without_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_v4(path=V4_CANDIDATE):
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=object_without_duplicate_keys,
    )


def assert_safe_path(test, value, *, base_name_only=False):
    test.assertIsInstance(value, str)
    test.assertNotEqual(value, "")
    test.assertNotIn("\\", value)
    test.assertNotIn("\x00", value)
    test.assertNotIn(":", value)
    path = PurePosixPath(value)
    test.assertFalse(path.is_absolute())
    test.assertNotIn("..", path.parts)
    if base_name_only:
        test.assertEqual(len(path.parts), 1)


def assert_v4_semantics(test, manifest):
    test.assertEqual(manifest.get("schema_version"), 4)
    assets = manifest.get("assets")
    test.assertIsInstance(assets, list)
    test.assertGreater(len(assets), 0)

    asset_ids = set()
    asset_urls = set()
    for asset in assets:
        test.assertIsInstance(asset, dict)
        asset_id = asset.get("id")
        test.assertIsInstance(asset_id, str)
        test.assertRegex(asset_id, SAFE_ID)
        test.assertNotIn(asset_id, asset_ids)
        asset_ids.add(asset_id)

        for field in ("provider", "kind", "version", "platform", "license", "attribution"):
            test.assertIsInstance(asset.get(field), str)
            test.assertNotEqual(asset[field].strip(), "")

        assert_safe_path(test, asset.get("file"), base_name_only=True)
        parsed = urlparse(asset.get("url", ""))
        test.assertEqual(parsed.scheme, "https")
        test.assertEqual(parsed.hostname, "forgejo.g-grp.com")
        test.assertIsNone(parsed.username)
        test.assertIsNone(parsed.password)
        test.assertIsNone(parsed.port)
        test.assertEqual(parsed.query, "")
        test.assertEqual(parsed.fragment, "")
        parts = tuple(part for part in parsed.path.split("/") if part)
        test.assertEqual(parts[:4], ("Max", "teammanager-models", "releases", "download"))
        test.assertEqual(len(parts), 6)
        test.assertRegex(asset.get("release_tag", ""), SAFE_ID)
        test.assertEqual(parts[-2], asset["release_tag"])
        test.assertEqual(parts[-1], asset["file"])
        test.assertNotIn(asset["url"], asset_urls)
        asset_urls.add(asset["url"])

        test.assertIs(type(asset.get("size_bytes")), int)
        test.assertGreater(asset["size_bytes"], 0)
        test.assertIsInstance(asset.get("sha256"), str)
        test.assertRegex(asset["sha256"], LOWER_SHA256)
        if "extracted_root" in asset:
            assert_safe_path(test, asset["extracted_root"])
        for field, value in asset.get("layout", {}).items():
            if field.endswith("_path") or field.endswith("_dir"):
                assert_safe_path(test, value)

        member_paths = set()
        for member in asset.get("members", []):
            assert_safe_path(test, member.get("path"))
            test.assertNotIn(member["path"], member_paths)
            member_paths.add(member["path"])
            test.assertIs(type(member.get("size_bytes")), int)
            test.assertGreater(member["size_bytes"], 0)
            test.assertRegex(member.get("sha256", ""), LOWER_SHA256)

    profiles = manifest.get("profiles")
    test.assertIsInstance(profiles, dict)
    test.assertGreater(len(profiles), 0)
    for profile_id, profile in profiles.items():
        test.assertRegex(profile_id, SAFE_ID)
        references = []
        if "asset_ids" in profile:
            references.extend(profile["asset_ids"])
        else:
            references.extend([profile["runtime_asset_id"], profile["default_model_id"]])
            references.extend(profile.get("optional_model_ids", []))
        test.assertEqual(len(references), len(set(references)))
        test.assertTrue(set(references).issubset(asset_ids))
        if "server_executable" in profile:
            assert_safe_path(test, profile["server_executable"])
        for dll in profile.get("required_dlls", []):
            assert_safe_path(test, dll)
            test.assertTrue(dll.lower().endswith(".dll"))

    packs = manifest.get("packs")
    test.assertIsInstance(packs, list)
    pack_ids = set()
    for pack in packs:
        test.assertRegex(pack.get("id", ""), SAFE_ID)
        test.assertNotIn(pack["id"], pack_ids)
        pack_ids.add(pack["id"])
        test.assertIsInstance(pack.get("kind"), str)
        test.assertIsInstance(pack.get("display_name"), str)
        test.assertGreater(len(pack.get("asset_ids", [])), 0)
        test.assertEqual(len(pack["asset_ids"]), len(set(pack["asset_ids"])))
        test.assertTrue(set(pack["asset_ids"]).issubset(asset_ids))


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

    def test_unpublished_v4_candidate_is_semantically_valid(self):
        manifest = load_v4()
        assert_v4_semantics(self, manifest)

        ids = {asset["id"] for asset in manifest["assets"]}
        self.assertEqual(len(manifest["assets"]), 16)
        self.assertEqual(ids, POCKET_DEFAULTS | POCKET_LANGUAGES | WHISPER)

    def test_v4_profiles_and_packs_reference_each_unique_asset(self):
        manifest = load_v4()
        pocket = manifest["profiles"]["pocket-default-windows"]
        whisper = manifest["profiles"]["whisper-default-windows"]

        self.assertEqual(set(pocket["asset_ids"]), POCKET_DEFAULTS)
        self.assertEqual(
            {
                whisper["runtime_asset_id"],
                whisper["default_model_id"],
                *whisper["optional_model_ids"],
            },
            WHISPER,
        )
        self.assertEqual(len(manifest["packs"]), 10)
        self.assertEqual(
            {asset_id for pack in manifest["packs"] for asset_id in pack["asset_ids"]},
            POCKET_LANGUAGES,
        )
        self.assertTrue(all("archives" not in pack for pack in manifest["packs"]))
        self.assertNotIn("optional", manifest)

    def test_v4_pocket_assets_match_current_catalog_artifact_identities(self):
        current = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        bundles = current["assets"]["pocket_bundles"]
        current_assets = [
            bundles["default_windows"]["runtime"],
            bundles["default_windows"]["english_model"],
            bundles["default_windows"]["catalog_voice"],
            *(archive for pack in bundles["language_packs"] for archive in pack["archives"]),
        ]
        candidate_assets = {asset["id"]: asset for asset in load_v4()["assets"]}

        self.assertEqual(len(current_assets), 13)
        for current_asset in current_assets:
            candidate = candidate_assets[current_asset["id"]]
            self.assertEqual(
                (
                    candidate["url"],
                    candidate["file"],
                    candidate["size_bytes"],
                    candidate["sha256"],
                ),
                (
                    current_asset["url"].replace("{base_url}", current["base_url"]),
                    current_asset["file"],
                    current_asset["size_bytes"],
                    current_asset["sha256"],
                ),
            )

    def test_v4_whisper_assets_match_active_release_metadata(self):
        assets = {asset["id"]: asset for asset in load_v4()["assets"]}
        expected = {
            "whispercpp-runtime-windows-amd64-1.9.1": (
                4505044,
                "6ac6eecf51eb0e84bf091bc06d7c2dbb700fef3e4b4e38bb6de1b852b47ba0b6",
            ),
            "whisper-base-q5_1": (
                59707625,
                "422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898",
            ),
            "whisper-small-q5_1": (
                190085487,
                "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb",
            ),
        }
        for asset_id, (size, digest) in expected.items():
            self.assertEqual(assets[asset_id]["size_bytes"], size)
            self.assertEqual(assets[asset_id]["sha256"], digest)

    def test_v4_semantics_tolerate_unknown_additive_fields(self):
        manifest = load_v4()
        manifest["future_top_level"] = {"version": 1}
        manifest["assets"][0]["future_asset_field"] = ["supported"]
        manifest["profiles"]["pocket-default-windows"]["future_profile_field"] = True
        manifest["packs"][0]["future_pack_field"] = 42

        assert_v4_semantics(self, manifest)

    def test_v4_semantics_reject_duplicate_ids_and_references(self):
        manifest = load_v4()
        manifest["assets"].append(copy.deepcopy(manifest["assets"][0]))
        with self.assertRaises(AssertionError):
            assert_v4_semantics(self, manifest)

        manifest = load_v4()
        manifest["profiles"]["pocket-default-windows"]["asset_ids"].append("missing-asset")
        with self.assertRaises(AssertionError):
            assert_v4_semantics(self, manifest)

    def test_v4_semantics_reject_bad_url_size_hash_and_paths(self):
        mutations = (
            lambda manifest: manifest["assets"][0].update(url="https://example.com/runtime.zip"),
            lambda manifest: manifest["assets"][0].update(size_bytes=0),
            lambda manifest: manifest["assets"][0].update(sha256=manifest["assets"][0]["sha256"].upper()),
            lambda manifest: manifest["assets"][0]["layout"].update(worker_path="../worker.py"),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                manifest = load_v4()
                mutate(manifest)
                with self.assertRaises(AssertionError):
                    assert_v4_semantics(self, manifest)

    def test_v4_loader_rejects_duplicate_json_object_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version": 4, "schema_version": 5}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                load_v4(path)

    def test_v4_candidate_has_no_source_signature_or_hash_sidecar(self):
        self.assertFalse(Path(f"{V4_CANDIDATE}.sig").exists())
        self.assertFalse(Path(f"{V4_CANDIDATE}.sha256").exists())


if __name__ == "__main__":
    unittest.main()
