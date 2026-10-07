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

    def check(self, sizes=None):
        files = dict(self.files)
        files[packager.MANIFEST_MEMBER] = json.dumps(self.manifest).encode()
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        if sizes is None:
            sizes = {name: len(data) for name, data in files.items()}
        with patch.object(packager, "SOURCE_SIZE", self.archive.stat().st_size), patch.object(
            packager, "SOURCE_SHA256", packager.sha256_file(self.archive)
        ), patch.object(
            packager, "SOURCE_MEMBER_SIZES", sizes
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


if __name__ == "__main__":
    unittest.main()
