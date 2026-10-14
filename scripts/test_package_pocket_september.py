#!/usr/bin/env python3
"""Focused source-archive checks for the Pocket English packager."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


spec = importlib.util.spec_from_file_location(
    "package_pocket", Path(__file__).with_name("package-pocket-september.py")
)
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class SourceChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "source.zip"
        graph_names = [
            name for name in packager.INPUT_TO_OUTPUT if name.endswith(".onnx")
        ]
        self.files = {name: name.encode() for name in packager.INPUT_TO_OUTPUT}
        self.manifest = {
            "cpp_models": [
                {
                    "path": name[len(packager.SOURCE_ROOT) + 1 :],
                    "sha256": hashlib.sha256(self.files[name]).hexdigest(),
                }
                for name in graph_names
            ],
            "tokenizer_sha256": hashlib.sha256(
                self.files[f"{packager.SOURCE_ROOT}/weights/tokenizer.model"]
            ).hexdigest(),
        }

    def source_members(self):
        files = dict(self.files)
        files[packager.MANIFEST_MEMBER] = json.dumps(self.manifest).encode()
        return files

    def write_source(self):
        files = self.source_members()
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return files

    def pinned_source(self, files):
        sizes = {name: len(data) for name, data in files.items()}
        return patch.multiple(
            packager,
            SOURCE_SIZE=self.archive.stat().st_size,
            SOURCE_SHA256=packager.sha256_file(self.archive),
            SOURCE_MEMBER_SIZES=sizes,
        )

    def check(self, sizes=None):
        files = self.write_source()
        if sizes is None:
            sizes = {name: len(data) for name, data in files.items()}
        with patch.multiple(
            packager,
            SOURCE_SIZE=self.archive.stat().st_size,
            SOURCE_SHA256=packager.sha256_file(self.archive),
            SOURCE_MEMBER_SIZES=sizes,
        ):
            return packager.checked_source(self.archive)

    def test_valid_manifest(self):
        self.assertEqual(len(self.check()), 6)

    def test_tampered_graph(self):
        graph = next(name for name in self.files if name.endswith(".onnx"))
        self.files[graph] = b"altered graph"
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.check()

    def test_unsafe_path(self):
        self.files["../escape"] = b"bad"
        with self.assertRaisesRegex(ValueError, "unsafe ZIP member path"):
            self.check()

    def test_member_size_bound(self):
        sizes = {name: len(data) for name, data in self.files.items()}
        sizes[packager.MANIFEST_MEMBER] = len(json.dumps(self.manifest).encode())
        sizes[next(iter(sizes))] += 1
        with self.assertRaisesRegex(ValueError, "member sizes"):
            self.check(sizes)

    def test_package_records_deterministic_archive_members(self):
        files = self.write_source()
        first_path = Path(self.temp.name) / "first.zip"
        second_path = Path(self.temp.name) / "second.zip"
        with self.pinned_source(files):
            first = packager.package(self.archive, first_path)
            second = packager.package(self.archive, second_path)

        self.assertEqual(first, second)
        self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        archive_hash = hashlib.sha256(first_path.read_bytes()).hexdigest()
        self.assertEqual(
            first["archive"],
            {"size_bytes": first_path.stat().st_size, "sha256": archive_hash},
        )

        expected_members = {
            **{
                output: self.files[source]
                for source, output in packager.INPUT_TO_OUTPUT.items()
            },
            "NOTICE.md": packager.NOTICE_PATH.read_bytes(),
            packager.LICENSE_MEMBER: packager.LICENSE_PATH.read_bytes(),
        }
        with zipfile.ZipFile(first_path) as bundle:
            self.assertEqual(bundle.namelist(), sorted(expected_members))
            for name, content in expected_members.items():
                info = bundle.getinfo(name)
                self.assertEqual(bundle.read(name), content)
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.external_attr, 0o100644 << 16)
                self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
                self.assertEqual(
                    first["members"][name],
                    {
                        "size_bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    },
                )

    def test_source_change_keeps_destination_and_cleans_partial(self):
        files = self.write_source()
        output = Path(self.temp.name) / "published.zip"
        partial = output.with_name(output.name + ".partial")
        previous = b"existing immutable destination"
        output.write_bytes(previous)
        checked_source = packager.checked_source

        def check_then_change_source(path):
            expected = checked_source(path)
            changed = self.source_members()
            source_name = next(name for name in self.files if name.endswith(".onnx"))
            changed[source_name] = b"changed after verification"
            with zipfile.ZipFile(path, "w") as archive:
                for name, content in changed.items():
                    archive.writestr(name, content)
            return expected

        with self.pinned_source(files), patch.object(
            packager, "checked_source", side_effect=check_then_change_source
        ):
            with self.assertRaisesRegex(ValueError, "source changed while packaging"):
                packager.package(self.archive, output)

        self.assertEqual(output.read_bytes(), previous)
        self.assertFalse(partial.exists())


if __name__ == "__main__":
    unittest.main()
