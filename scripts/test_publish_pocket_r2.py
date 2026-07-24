from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("publish-pocket-r2.py")
SPEC = importlib.util.spec_from_file_location("publish_pocket_r2", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PublishPocketR2Tests(unittest.TestCase):
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
                state_name = MODULE.R2_VOICE_ROOT + "voice/alba.safetensors"
                self.assertIn(state_name, names)
                self.assertEqual(archive.read(state_name), b"official-alba-fixture")
                self.assertIn(MODULE.R2_VOICE_ROOT + "upstream-source.json", names)


if __name__ == "__main__":
    unittest.main()
