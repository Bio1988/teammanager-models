import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


spec = importlib.util.spec_from_file_location(
    "package_managed_radio_assets",
    Path(__file__).with_name("package_managed_radio_assets.py"),
)
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class ManagedRadioAssetsTest(unittest.TestCase):
    def test_documented_candidate_pins_match_packager(self):
        document = (packager.ROOT / "docs/managed-radio-assets.md").read_text()
        for value in (
            packager.RELEASE_TAG,
            packager.RUNTIME_SOURCE_COMMIT,
            packager.RUNTIME_SOURCE_SHA256,
            packager.MODEL_SOURCE_REPO,
            packager.MODEL_SOURCE_REVISION,
            packager.MODEL_SOURCE_SHA256,
            "prepared-not-published",
        ):
            self.assertIn(value, document)

    def fixture(self, root, unsafe=False):
        sources = root / "sources"
        sources.mkdir()
        model = b"fixture GGUF bytes"
        (sources / packager.MODEL_SOURCE).write_bytes(model)
        runtime = sources / packager.RUNTIME_SOURCE
        with zipfile.ZipFile(runtime, "w") as bundle:
            bundle.writestr("llama-server.exe", b"server")
            bundle.writestr("ggml-base.dll", b"base")
            bundle.writestr("libomp140.x86_64.dll", b"openmp")
            bundle.writestr("llama-cli.exe", b"not included")
            if unsafe:
                bundle.writestr("../escape.dll", b"unsafe")
        patches = (
            patch.object(packager, "RUNTIME_SOURCE_SIZE", runtime.stat().st_size),
            patch.object(packager, "RUNTIME_SOURCE_SHA256", packager.sha256_file(runtime)),
            patch.object(packager, "MODEL_SOURCE_SIZE", len(model)),
            patch.object(packager, "MODEL_SOURCE_SHA256", hashlib.sha256(model).hexdigest()),
        )
        return sources, patches

    def test_build_is_deterministic_and_has_a_closed_root_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, patches = self.fixture(root)
            with patches[0], patches[1], patches[2], patches[3]:
                first = packager.build(sources, root / "first")
                second = packager.build(sources, root / "second")

            for name in ("runtime-b8696-win-cpu-x64.zip", "granite-4.0-h-350m-q8-0.zip"):
                first_bytes = (root / "first" / name).read_bytes()
                self.assertEqual(first_bytes, (root / "second" / name).read_bytes())
                with zipfile.ZipFile(root / "first" / name) as bundle:
                    self.assertIsNone(bundle.testzip())
                    self.assertEqual(bundle.namelist(), sorted(bundle.namelist()))
                    for info in bundle.infolist():
                        self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                        self.assertEqual(info.external_attr, 0o100644 << 16)
                        self.assertNotIn("/", info.filename)

            with zipfile.ZipFile(root / "first" / "runtime-b8696-win-cpu-x64.zip") as bundle:
                names = set(bundle.namelist())
                self.assertIn("llama-server.exe", names)
                self.assertEqual({name for name in names if name.lower().endswith(".dll")}, {
                    "ggml-base.dll",
                    "libomp140.x86_64.dll",
                })
                self.assertNotIn("llama-cli.exe", names)

            self.assertEqual(first["packages"][0]["ArchiveSHA256"], second["packages"][0]["ArchiveSHA256"])
            self.assertEqual(first["packages"][1]["ArchiveSHA256"], second["packages"][1]["ArchiveSHA256"])
            self.assertEqual(first["release"]["state"], "prepared-not-published")

    def test_rejects_unsafe_upstream_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, patches = self.fixture(root, unsafe=True)
            with patches[0], patches[1], patches[2], patches[3]:
                with self.assertRaisesRegex(ValueError, "unsafe ZIP member name"):
                    packager.build(sources, root / "out")


if __name__ == "__main__":
    unittest.main()
