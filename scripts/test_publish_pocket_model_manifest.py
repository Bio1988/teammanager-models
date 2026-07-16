import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("publish-pocket-model-manifest.py")
SPEC = importlib.util.spec_from_file_location("publish_pocket_model_manifest", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class PocketModelAuthorityTests(unittest.TestCase):
    def fixture(self, root: Path):
        files = {
            module.RUNTIME_ARCHIVE: b"runtime-fixture",
            module.VOICE_ARCHIVE: b"alba-fixture",
        }
        for name, data in files.items():
            (root / name).write_bytes(data)
        model_bytes = b"real-english-clone-capable-model-fixture"
        config_bytes = b"weights_path: weights/model.safetensors\n"
        with zipfile.ZipFile(root / module.MODEL_ARCHIVE, "w") as bundle:
            bundle.writestr(module.MODEL_MEMBER, model_bytes)
            bundle.writestr(module.CONFIG_MEMBER, config_bytes)
        def asset(name, file):
            return {"package_version": "2.1.0", "model_revision": module.ENGLISH_MODEL_REVISION,
                    "release_tag": module.CANONICAL_RELEASE, "file": file,
                    "sha256": module.sha256(root / file)}
        manifest = {"version": "3", "assets": {"pocket_bundles": {"default_windows": {
            "model_revision": module.ENGLISH_MODEL_REVISION,
            "runtime": asset("runtime", module.RUNTIME_ARCHIVE),
            "english_model": asset("model", module.MODEL_ARCHIVE),
            "catalog_voice": asset("voice", module.VOICE_ARCHIVE),
        }}}}
        return manifest, model_bytes, config_bytes

    def test_derives_one_english_authority_from_canonical_archive_members(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, model_bytes, config_bytes = self.fixture(root)
            model = module.build_model(manifest, root)
            self.assertEqual([row["language"] for row in model["clone_languages"]], ["english"])
            self.assertEqual(model["model_sha256"], hashlib.sha256(model_bytes).hexdigest())
            self.assertEqual(model["model_config_sha256"], hashlib.sha256(config_bytes).hexdigest())
            self.assertEqual(model["clone_languages"][0]["cloning_weights_sha256"], model["model_sha256"])

    def test_rejects_release_archive_member_and_multilingual_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, _, _ = self.fixture(root)
            manifest["assets"]["pocket_bundles"]["default_windows"]["runtime"]["release_tag"] = "pocket-tts-clone-weights-v2.1.0-r1"
            with self.assertRaisesRegex(ValueError, "canonical runtime"):
                module.build_model(manifest, root)
            manifest, _, _ = self.fixture(root)
            (root / module.MODEL_ARCHIVE).write_bytes(b"altered")
            with self.assertRaisesRegex(ValueError, "archive bytes"):
                module.build_model(manifest, root)
            manifest, _, _ = self.fixture(root)
            model = module.build_model(manifest, root)
            model["clone_languages"].append(dict(model["clone_languages"][0], language="german"))
            with self.assertRaisesRegex(ValueError, "exactly English"):
                module.validate_state_compatibility_model(model)

    def test_signs_exact_manifest_bytes_and_verifies_raw_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest, _, _ = self.fixture(root)
            (root / "manifest.json").write_text(json.dumps(manifest))
            subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519", "-out", root / "key.pem"], check=True)
            subprocess.run(["openssl", "pkey", "-in", root / "key.pem", "-pubout", "-out", root / "key.pub"], check=True)
            args = type("Args", (), dict(
                manifest=root / "manifest.json", artifact_root=root,
                signing_key=root / "key.pem", public_key=root / "key.pub",
                output_dir=root / "out", updated_manifest=root / "updated.json",
            ))()
            module.publish(args)
            published = root / "out/teammanager-model-manifest-v3.json"
            signature = published.with_suffix(".json.sig")
            self.assertEqual(signature.stat().st_size, 64)
            module.verify_signature(root / "key.pub", published, signature)
            self.assertEqual(published.with_suffix(".json.sha256").read_text(), module.sha256(published) + "\n")
            self.assertEqual((root / "updated.json").read_bytes(), published.read_bytes())


if __name__ == "__main__":
    unittest.main()
