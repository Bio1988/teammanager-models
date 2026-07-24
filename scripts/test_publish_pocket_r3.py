from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("publish-pocket-r3.py")
SPEC = importlib.util.spec_from_file_location("publish_pocket_r3", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PublishPocketR3Tests(unittest.TestCase):
    def test_worker_markers_cover_clone_contract(self) -> None:
        self.assertIn('WORKER_VERSION = "0.3.0"', MODULE.REQUIRED_WORKER_MARKERS)
        self.assertIn('"voice-clone-v1"', MODULE.REQUIRED_WORKER_MARKERS)
        self.assertIn('"voice-state-synthesis-v1"', MODULE.REQUIRED_WORKER_MARKERS)

    def test_official_alba_archive_layout_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            alba = root_path / "alba.safetensors"
            alba.write_bytes(b"official-alba-fixture")
            old_digest = MODULE.OFFICIAL_ALBA_SHA256
            MODULE.OFFICIAL_ALBA_SHA256 = MODULE.sha256(alba)
            try:
                output = root_path / "voice.zip"
                MODULE.build_voice(alba, output)
            finally:
                MODULE.OFFICIAL_ALBA_SHA256 = old_digest
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                state_name = MODULE.R3_VOICE_ROOT + "voice/alba.safetensors"
                self.assertIn(state_name, names)
                self.assertEqual(archive.read(state_name), b"official-alba-fixture")
                self.assertIn(MODULE.R3_VOICE_ROOT + "upstream-source.json", names)

    def test_runtime_contains_clone_compatibility_authority(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            base = root_path / "base.zip"
            worker = root_path / "worker.py"
            output = root_path / "runtime.zip"
            worker.write_text("\n".join(MODULE.REQUIRED_WORKER_MARKERS), encoding="utf-8")
            metadata = {"bundle_kind": "runtime"}
            with zipfile.ZipFile(base, "w") as archive:
                archive.writestr(MODULE.BASE_RUNTIME_ROOT + "worker.py", b"old")
                archive.writestr(
                    MODULE.BASE_RUNTIME_ROOT + "bundle-build.json",
                    json.dumps(metadata).encode("utf-8"),
                )
            old_digest = MODULE.BASE_RUNTIME_SHA256
            MODULE.BASE_RUNTIME_SHA256 = MODULE.sha256(base)
            try:
                MODULE.build_runtime(base, worker, output)
            finally:
                MODULE.BASE_RUNTIME_SHA256 = old_digest
            with zipfile.ZipFile(output) as archive:
                built = json.loads(
                    archive.read(MODULE.R3_RUNTIME_ROOT + "bundle-build.json")
                )
            self.assertEqual(
                built["state_compatibility_runtime"]["schema"],
                "pocket-state-runtime-v1",
            )


if __name__ == "__main__":
    unittest.main()
