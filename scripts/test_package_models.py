import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


spec = importlib.util.spec_from_file_location(
    "package_moonshine_models", Path(__file__).with_name("package-moonshine-models.py")
)
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class PackageModelsTest(unittest.TestCase):
    def test_archive_is_identical_on_windows_and_unix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {"tokenizer.bin": b"fixture tokenizer", "adapter.ort": b"fixture model"}
            for name, data in files.items():
                (root / name).write_bytes(data)
            models = {"fixture": {"archive": "fixture.zip", "files": files}}
            archives = []
            for platform in ("linux", "win32"):
                output = root / platform
                with (
                    patch.object(packager, "MODELS", models),
                    patch.object(packager, "fetch", side_effect=lambda model, name, cache: root / name),
                    patch.object(sys, "argv", ["package-moonshine-models.py", "--out", str(output)]),
                    patch.object(zipfile.sys, "platform", platform),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    packager.main()
                archive = (output / "fixture.zip").read_bytes()
                archives.append(archive)
                record = json.loads((output / "moonshine-model-records.json").read_text())["fixture.zip"]
                self.assertEqual(record["size_bytes"], len(archive))
                self.assertEqual(record["sha256"], hashlib.sha256(archive).hexdigest())
                with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                    self.assertEqual(bundle.namelist(), sorted(files))
                    for name, data in files.items():
                        self.assertEqual(bundle.read(name), data)
                        self.assertEqual(bundle.getinfo(name).date_time, (1980, 1, 1, 0, 0, 0))
                        self.assertEqual(bundle.getinfo(name).create_system, 3)
                        self.assertEqual(bundle.getinfo(name).external_attr, 0o644 << 16)
            self.assertEqual(archives[0], archives[1])


if __name__ == "__main__":
    unittest.main()
