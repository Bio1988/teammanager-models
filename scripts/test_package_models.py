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
    @staticmethod
    def fixture_models(content):
        return {
            "fixture": {
                "archive": "fixture.zip",
                "files": {
                    "model.bin": (len(content), hashlib.sha256(content).hexdigest())
                },
            }
        }

    def write_fetch_target(self, root, content):
        target = root / "fixture" / "model.bin"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def download_side_effect(self, content):
        def download(command, check):
            self.assertTrue(check)
            partial = Path(command[command.index("-o") + 1])
            partial.write_bytes(content)

        return download

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

    def test_fetch_uses_verified_cache_without_downloading(self):
        content = b"verified model"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = self.write_fetch_target(root, content)
            with patch.object(packager, "MODELS", self.fixture_models(content)), patch.object(
                packager.subprocess, "run"
            ) as run:
                result = packager.fetch("fixture", "model.bin", root)

            self.assertEqual(Path(result), target)
            run.assert_not_called()

    def test_fetch_replaces_corrupt_cache_only_after_verified_download(self):
        content = b"approved payload"
        corrupt_cache = b"old corrupt cache"
        rejected = b"tampered payload"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = self.write_fetch_target(root, corrupt_cache)
            calls = []

            def download(command, check):
                self.assertEqual(target.read_bytes(), corrupt_cache)
                payload = (rejected, content)[len(calls)]
                calls.append(payload)
                Path(command[command.index("-o") + 1]).write_bytes(payload)

            with contextlib.redirect_stderr(io.StringIO()), patch.object(
                packager, "MODELS", self.fixture_models(content)
            ), patch.object(packager.subprocess, "run", side_effect=download):
                result = packager.fetch("fixture", "model.bin", root)

            self.assertEqual(Path(result), target)
            self.assertEqual(calls, [rejected, content])
            self.assertEqual(target.read_bytes(), content)
            self.assertFalse(Path(str(target) + ".partial").exists())

    def test_fetch_rejects_wrong_size_or_hash_after_bounded_attempts(self):
        content = b"approved"
        cases = (("wrong size", b"different-size"), ("wrong hash", b"tampered"))
        for label, rejected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                cached = b"old invalid cache"
                target = self.write_fetch_target(root, cached)
                with contextlib.redirect_stderr(io.StringIO()), patch.object(
                    packager, "MODELS", self.fixture_models(content)
                ), patch.object(
                    packager.subprocess,
                    "run",
                    side_effect=self.download_side_effect(rejected),
                ) as run:
                    with self.assertRaisesRegex(SystemExit, "unable to fetch verified"):
                        packager.fetch("fixture", "model.bin", root)

                self.assertEqual(run.call_count, 4)
                self.assertEqual(target.read_bytes(), cached)
                self.assertFalse(Path(str(target) + ".partial").exists())


if __name__ == "__main__":
    unittest.main()
