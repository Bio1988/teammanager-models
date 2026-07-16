import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("publish-whisper-authority.py")
SPEC = importlib.util.spec_from_file_location("publish_whisper_authority", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class WhisperAuthorityPublisherTests(unittest.TestCase):
    def fixture(self, root: Path):
        runtime = root / module.RUNTIME_FILE
        model = root / module.MODEL_FILE
        release = root / module.MANIFEST_FILE
        member_bytes = b"runtime-only-executable"
        with zipfile.ZipFile(runtime, "w") as archive:
            archive.writestr("Release/whisper-server.exe", member_bytes)
        model.write_bytes(b"base-q5_1-model")
        runtime_hash = module.sha256(runtime)
        model_hash = module.sha256(model)
        payload = {
            "schema_version": 3,
            "release_identity": "sha256:" + runtime_hash,
            "release_version": module.RUNTIME_RELEASE,
            "platform": module.PLATFORM,
            "runtime": {
                "archive_identity": "sha256:" + runtime_hash,
                "file_name": module.RUNTIME_FILE,
                "size_bytes": runtime.stat().st_size,
                "sha256": runtime_hash,
                "server_executable": "Release/whisper-server.exe",
                "members": [{
                    "path": "Release/whisper-server.exe",
                    "size_bytes": len(member_bytes),
                    "sha256": __import__("hashlib").sha256(member_bytes).hexdigest(),
                }],
            },
            "baseline_model": {
                "id": "base-q5_1", "release_identity": "sha256:" + model_hash,
                "release_version": module.MODEL_RELEASE, "file_name": module.MODEL_FILE,
                "size_bytes": model.stat().st_size, "sha256": model_hash,
            },
            "optional_models": {},
        }
        release.write_text(json.dumps(payload, indent=2) + "\n")
        module.REVIEWED_MANIFEST = (release.stat().st_size, module.sha256(release))
        module.REVIEWED_RUNTIME = (runtime.stat().st_size, runtime_hash)
        module.REVIEWED_MODEL = (model.stat().st_size, model_hash)
        key = root / "key.pem"
        public = root / "key.pub"
        return release, runtime, model, key, public

    def keys(self, root: Path):
        key, public = root / "key.pem", root / "key.pub"
        subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519", "-out", key], check=True)
        subprocess.run(["openssl", "pkey", "-in", key, "-pubout", "-out", public], check=True)
        der = subprocess.run(
            ["openssl", "pkey", "-pubin", "-in", public, "-outform", "DER"],
            check=True, capture_output=True,
        ).stdout
        module.REVIEWED_PUBLIC_KEY_HEX = der[-32:].hex()
        module.REVIEWED_PUBLIC_KEY_DER_SHA256 = __import__("hashlib").sha256(der).hexdigest()
        return key, public

    def test_publishes_domain_separated_exact_bytes_raw_signature_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            release, runtime, model, _, _ = self.fixture(root)
            key, public = self.keys(root)
            out = root / "out"
            args = type("Args", (), dict(
                release_manifest=release, runtime=runtime, model=model,
                signing_key=key, public_key=public, output_dir=out,
            ))()
            module.publish(args)
            authority = out / module.OUTPUT_FILE
            signature = authority.with_suffix(".json.sig")
            sidecar = authority.with_suffix(".json.sha256")
            self.assertEqual(signature.stat().st_size, 64)
            self.assertEqual(sidecar.read_text(), module.sha256(authority) + "\n")
            preimage = root / "preimage"
            preimage.write_bytes(module.DOMAIN + authority.read_bytes())
            subprocess.run([
                "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", public,
                "-rawin", "-in", preimage, "-sigfile", signature,
            ], check=True, stdout=subprocess.DEVNULL)
            parsed = json.loads(authority.read_bytes(), object_pairs_hook=module.reject_duplicate_names)
            self.assertEqual(parsed["schema"], module.SCHEMA)
            self.assertEqual(parsed["baseline_model"]["id"], "base-q5_1")
            module.validate_published(authority, signature, sidecar, release, runtime, model, public)

    def test_rejects_tampered_runtime_model_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            key, public = self.keys(root)
            del key
            for changed in (module.RUNTIME_FILE, module.MODEL_FILE, module.MANIFEST_FILE):
                release, runtime, model, _, _ = self.fixture(root)
                (root / changed).write_bytes((root / changed).read_bytes() + b"tampered")
                with self.assertRaises(ValueError):
                    module.build_authority(release, runtime, model, public)

    def test_rejects_archive_member_and_authority_tuple_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            release, runtime, model, _, _ = self.fixture(root)
            key, public = self.keys(root)
            payload = json.loads(release.read_text())
            payload["runtime"]["members"][0]["sha256"] = "0" * 64
            release.write_text(json.dumps(payload, indent=2) + "\n")
            module.REVIEWED_MANIFEST = (release.stat().st_size, module.sha256(release))
            with self.assertRaisesRegex(ValueError, "member bytes"):
                module.build_authority(release, runtime, model, public)

            release, runtime, model, _, _ = self.fixture(root)
            out = root / "out"
            args = type("Args", (), dict(
                release_manifest=release, runtime=runtime, model=model,
                signing_key=key, public_key=public, output_dir=out,
            ))()
            module.publish(args)
            authority = out / module.OUTPUT_FILE
            signature = authority.with_suffix(".json.sig")
            sidecar = authority.with_suffix(".json.sha256")
            original = authority.read_bytes()
            for target, replacement, message in (
                (authority, original + b" ", "closed deterministic"),
                (sidecar, b"0" * 64 + b"\n", "sidecar"),
                (signature, signature.read_bytes()[:-1], "64 bytes"),
            ):
                authority.write_bytes(original)
                module.publish(args)
                target.write_bytes(replacement)
                with self.assertRaisesRegex((ValueError, subprocess.CalledProcessError), message):
                    module.validate_published(authority, signature, sidecar, release, runtime, model, public)


if __name__ == "__main__":
    unittest.main()
