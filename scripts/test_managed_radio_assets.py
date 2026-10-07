import hashlib
import importlib.util
from contextlib import ExitStack
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
            packager.RUNTIME_RELEASE_TAG,
            packager.MODEL_RELEASE_TAG,
            packager.RUNTIME_SOURCE_COMMIT,
            packager.RUNTIME_SOURCE_SHA256,
            packager.REDIST_SOURCE_SHA256,
            packager.REDIST_SOURCE_REVISION,
            packager.REDIST_VERSION,
            packager.MODEL_SOURCE_REPO,
            packager.MODEL_SOURCE_REVISION,
            packager.MODEL_SOURCE_SHA256,
            "prepared-not-published",
        ):
            self.assertIn(value, document)

    def fixture(self, root, unsafe_runtime=False, unsafe_redist=False):
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
            if unsafe_runtime:
                bundle.writestr("../escape.dll", b"unsafe")
        redist = sources / packager.REDIST_SOURCE
        redist_files = {
            "msvcp140.dll": b"msvcp",
            "msvcp140_1.dll": b"not required",
            "vcruntime140.dll": b"vcruntime",
            "vcruntime140_1.dll": b"vcruntime one",
        }
        with zipfile.ZipFile(redist, "w") as bundle:
            for name, contents in redist_files.items():
                bundle.writestr(name, contents)
            if unsafe_redist:
                bundle.writestr("../escape.dll", b"unsafe")
        selected_redist = {
            name: (len(redist_files[name]), hashlib.sha256(redist_files[name]).hexdigest())
            for name in packager.REDIST_FILES
        }
        patches = (
            patch.object(packager, "RUNTIME_SOURCE_SIZE", runtime.stat().st_size),
            patch.object(packager, "RUNTIME_SOURCE_SHA256", packager.sha256_file(runtime)),
            patch.object(packager, "REDIST_SOURCE_SIZE", redist.stat().st_size),
            patch.object(packager, "REDIST_SOURCE_SHA256", packager.sha256_file(redist)),
            patch.object(packager, "REDIST_FILES", selected_redist),
            patch.object(packager, "MODEL_SOURCE_SIZE", len(model)),
            patch.object(packager, "MODEL_SOURCE_SHA256", hashlib.sha256(model).hexdigest()),
        )
        return sources, patches

    def test_build_is_deterministic_and_has_a_closed_root_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, patches = self.fixture(root)
            with ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                first = packager.build(sources, root / "first")
                second = packager.build(sources, root / "second")

            for name in ("runtime-b8696-win-cpu-x64-r2.zip", "granite-4.0-h-350m-q8-0.zip"):
                first_bytes = (root / "first" / name).read_bytes()
                self.assertEqual(first_bytes, (root / "second" / name).read_bytes())
                with zipfile.ZipFile(root / "first" / name) as bundle:
                    self.assertIsNone(bundle.testzip())
                    self.assertEqual(bundle.namelist(), sorted(bundle.namelist()))
                    for info in bundle.infolist():
                        self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                        self.assertEqual(info.external_attr, 0o100644 << 16)
                        self.assertNotIn("/", info.filename)

            with zipfile.ZipFile(root / "first" / "runtime-b8696-win-cpu-x64-r2.zip") as bundle:
                names = set(bundle.namelist())
                self.assertIn("llama-server.exe", names)
                self.assertEqual({name for name in names if name.lower().endswith(".dll")}, {
                    "ggml-base.dll",
                    "libomp140.x86_64.dll",
                    "msvcp140.dll",
                    "vcruntime140.dll",
                    "vcruntime140_1.dll",
                })
                self.assertIn("NOTICE-Microsoft-Visual-Cpp-Redistributable.txt", names)
                self.assertNotIn("msvcp140_1.dll", names)
                self.assertNotIn("llama-cli.exe", names)

            self.assertEqual(first["packages"][0]["ArchiveSHA256"], second["packages"][0]["ArchiveSHA256"])
            self.assertEqual(first["packages"][1]["ArchiveSHA256"], second["packages"][1]["ArchiveSHA256"])
            self.assertEqual(first["format_version"], 2)
            self.assertEqual(first["release"]["runtime_state"], "prepared-not-published")
            self.assertEqual(first["release"]["model_state"], "published-immutable")

    def test_rejects_unsafe_upstream_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, patches = self.fixture(root, unsafe_runtime=True)
            with ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                with self.assertRaisesRegex(ValueError, "unsafe ZIP member name"):
                    packager.build(sources, root / "out")

    def test_rejects_unsafe_redistributable_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, patches = self.fixture(root, unsafe_redist=True)
            with ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                with self.assertRaisesRegex(ValueError, "unsafe ZIP member name"):
                    packager.build(sources, root / "out")

    def test_rejects_changed_redistributable_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, patches = self.fixture(root)
            with ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                expected = dict(packager.REDIST_FILES)
                size, _digest = expected["msvcp140.dll"]
                expected["msvcp140.dll"] = (size, "0" * 64)
                stack.enter_context(patch.object(packager, "REDIST_FILES", expected))
                with self.assertRaisesRegex(ValueError, "redistributable member size or SHA-256 mismatch"):
                    packager.build(sources, root / "out")


if __name__ == "__main__":
    unittest.main()
