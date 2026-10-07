#!/usr/bin/env python3
"""Build the two closed, deterministic optional managed-radio ZIPs."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_RELEASE_TAG = "managed-radio-granite-350m-r2"
MODEL_RELEASE_TAG = "managed-radio-granite-350m-r1"
RELEASE_ROOT = "https://forgejo.g-grp.com/Max/teammanager-models/releases/download"
RUNTIME_RELEASE_BASE = f"{RELEASE_ROOT}/{RUNTIME_RELEASE_TAG}"
MODEL_RELEASE_BASE = f"{RELEASE_ROOT}/{MODEL_RELEASE_TAG}"

RUNTIME_SOURCE = "llama-b8696-bin-win-cpu-x64.zip"
RUNTIME_SOURCE_SIZE = 39_345_159
RUNTIME_SOURCE_SHA256 = "8e0e2a0d86b5d3f4795a89edb60dc82f70a430dac69897f12e81f2f0cd5260d4"
RUNTIME_SOURCE_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b8696/llama-b8696-bin-win-cpu-x64.zip"
RUNTIME_SOURCE_COMMIT = "69c28f1547c169902f62ca48bee75fb876c4d8e6"
REDIST_SOURCE = "teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip"
REDIST_SOURCE_SIZE = 11_455_945
REDIST_SOURCE_SHA256 = "718dca3a95fd02eeb02f483fa750500a51a24576dc099c507de48af154c48335"
REDIST_SOURCE_URL = (
    "https://forgejo.g-grp.com/Max/teammanager-models/releases/download/"
    "moonshine-v0.1.5/teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip"
)
REDIST_SOURCE_REVISION = "234f60faa0eb388b01cdf7e60aca232af37aefda"
REDIST_VERSION = "14.44.35211.0"
REDIST_FILES = {
    "msvcp140.dll": (
        557_728,
        "0f885b509a685d2bbfa652fed26b5fb31d88fbdab0a978c641d1c7b8aa460aa9",
    ),
    "vcruntime140.dll": (
        124_544,
        "d5e4d9a3e835fa679450145d6a7d94e36573a509317111904d9b3712c30d9066",
    ),
    "vcruntime140_1.dll": (
        49_792,
        "1f2d41c4aa5db0bc33ebf7b66d72943a817d7ce6cbe880502a9403823633093f",
    ),
}
RUNTIME_LICENSES = {
    "LICENSE-llama.cpp-MIT.txt": (
        "llama.cpp-MIT.txt",
        "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d",
        "https://raw.githubusercontent.com/ggml-org/llama.cpp/69c28f1547c169902f62ca48bee75fb876c4d8e6/LICENSE",
    ),
    "LICENSE-cpp-httplib-MIT.txt": (
        "cpp-httplib-MIT.txt",
        "4b45cbe16d7b71b89ae6127e26e0d90a029198ca5e958ad8e3d0b8bbed364d8b",
        "https://raw.githubusercontent.com/ggml-org/llama.cpp/69c28f1547c169902f62ca48bee75fb876c4d8e6/vendor/cpp-httplib/LICENSE",
    ),
    "LICENSE-nlohmann-json-MIT.txt": (
        "nlohmann-json-MIT.txt",
        "c0d068392ea65358b798b8c165103560f06e9e3b38c4ab4e2d8810a7b931af86",
        "https://raw.githubusercontent.com/ggml-org/llama.cpp/69c28f1547c169902f62ca48bee75fb876c4d8e6/licenses/LICENSE-jsonhpp",
    ),
    "LICENSE-libomp-Apache-2.0-with-LLVM-exception.txt": (
        "LLVM-20.1.8-Apache-2.0-with-LLVM-exception.txt",
        "3340babe8ac7bc6ae294d93aa01c310a250d43d5b760e5c12954882d4e5c83c7",
        "https://github.com/llvm/llvm-project/releases/tag/llvmorg-20.1.8",
    ),
    "NOTICE-Microsoft-Visual-Cpp-Redistributable.txt": (
        "Microsoft-Visual-Cpp-Redistributable-NOTICE.txt",
        "c386b552f0b37ea63eb452b8a60a7f711c21fdf48093170250aeda36fb27ecf8",
        "https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution",
    ),
}

MODEL_SOURCE = "granite-4.0-h-350m-Q8_0.gguf"
MODEL_SOURCE_SIZE = 366_195_616
MODEL_SOURCE_SHA256 = "c7d9873640dc303b6773dcc44e72e5bdf533e1c95ca8421e6191fbff5c94c942"
MODEL_SOURCE_REPO = "ibm-granite/granite-4.0-h-350m-GGUF"
MODEL_SOURCE_REVISION = "a864f823cce6e6048b5752e2816fe7a23987d790"
MODEL_SOURCE_URL = (
    f"https://huggingface.co/{MODEL_SOURCE_REPO}/resolve/"
    f"{MODEL_SOURCE_REVISION}/{MODEL_SOURCE}"
)

APACHE_LICENSE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_flat_name(name):
    if not name or name in (".", "..") or PurePosixPath(name).name != name or "/" in name or "\\" in name or "\x00" in name:
        raise ValueError(f"unsafe ZIP member name: {name!r}")


def verify_source(path, expected_size, expected_sha256):
    path = Path(path)
    if path.stat().st_size != expected_size or sha256_file(path) != expected_sha256:
        raise ValueError(f"source size or SHA-256 mismatch: {path.name}")
    return path


def copy_member(archive, info, destination):
    destination = Path(destination)
    digest = hashlib.sha256()
    size = 0
    with archive.open(info) as source, destination.open("wb") as target:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
            target.write(chunk)
    if size != info.file_size:
        raise ValueError(f"source member size changed: {info.filename}")
    return {"size_bytes": size, "sha256": digest.hexdigest()}


def deterministic_zip(output_path, files):
    output_path = Path(output_path)
    names = list(files)
    if len(names) != len(set(names)):
        raise ValueError("duplicate output member names")
    for name in names:
        check_flat_name(name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_name(output_path.name + ".partial")
    try:
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_STORED) as bundle:
            for name in sorted(names):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o100644 << 16
                with Path(files[name]).open("rb") as source, bundle.open(info, "w") as target:
                    shutil.copyfileobj(source, target, 1 << 20)
        records = {}
        with zipfile.ZipFile(partial) as bundle:
            if bundle.testzip() or bundle.namelist() != sorted(names):
                raise ValueError("generated ZIP failed its closed inventory or CRC check")
            for name in sorted(names):
                info = bundle.getinfo(name)
                digest = hashlib.sha256()
                with bundle.open(name) as member:
                    for chunk in iter(lambda: member.read(1 << 20), b""):
                        digest.update(chunk)
                records[name] = {"size_bytes": info.file_size, "sha256": digest.hexdigest()}
        partial.replace(output_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return {
        "archive_size_bytes": output_path.stat().st_size,
        "archive_sha256": sha256_file(output_path),
        "files": records,
    }


def build(source_dir, output_dir, repo_root=ROOT):
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    runtime_input = verify_source(
        source_dir / RUNTIME_SOURCE, RUNTIME_SOURCE_SIZE, RUNTIME_SOURCE_SHA256
    )
    redist_input = verify_source(
        source_dir / REDIST_SOURCE, REDIST_SOURCE_SIZE, REDIST_SOURCE_SHA256
    )
    model_input = verify_source(
        source_dir / MODEL_SOURCE, MODEL_SOURCE_SIZE, MODEL_SOURCE_SHA256
    )

    license_root = Path(repo_root) / "LICENSES"
    runtime_licenses = {}
    for output_name, (source_name, expected_sha256, _url) in RUNTIME_LICENSES.items():
        license_path = license_root / source_name
        if sha256_file(license_path) != expected_sha256:
            raise ValueError(f"license text SHA-256 mismatch: {source_name}")
        runtime_licenses[output_name] = license_path
    apache_license = license_root / "Apache-2.0.txt"
    if sha256_file(apache_license) != APACHE_LICENSE_SHA256:
        raise ValueError("Apache license text does not match the pinned canonical text")

    runtime_source_members = []
    redist_source_members = []
    with tempfile.TemporaryDirectory(prefix="managed-radio-") as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(runtime_input) as source:
            infos = source.infolist()
            source_names = [item.filename for item in infos]
            if len(source_names) != len(set(source_names)):
                raise ValueError("duplicate member in pinned llama.cpp release ZIP")
            for info in infos:
                check_flat_name(info.filename)
                mode = stat.S_IFMT(info.external_attr >> 16)
                if info.is_dir() or mode not in (0, stat.S_IFREG) or info.flag_bits & 1:
                    raise ValueError(f"unsupported upstream ZIP member: {info.filename!r}")
            dlls = sorted(name for name in source_names if name.lower().endswith(".dll"))
            if not dlls or "llama-server.exe" not in source_names:
                raise ValueError("pinned CPU release lacks llama-server.exe or DLLs")
            runtime_files = {}
            for name in [*dlls, "llama-server.exe"]:
                check_flat_name(name)
                info = source.getinfo(name)
                copy_member(source, info, extracted / name)
                runtime_files[name] = extracted / name
                runtime_source_members.append(name)
        with zipfile.ZipFile(redist_input) as source:
            infos = source.infolist()
            source_names = [item.filename for item in infos]
            if len(source_names) != len(set(source_names)):
                raise ValueError("duplicate member in pinned redistributable source ZIP")
            for info in infos:
                check_flat_name(info.filename)
                mode = stat.S_IFMT(info.external_attr >> 16)
                if info.is_dir() or mode not in (0, stat.S_IFREG) or info.flag_bits & 1:
                    raise ValueError(f"unsupported redistributable source ZIP member: {info.filename!r}")
            for name, expected in REDIST_FILES.items():
                if name not in source_names:
                    raise ValueError(f"pinned redistributable source lacks {name}")
                details = copy_member(source, source.getinfo(name), extracted / name)
                if (details["size_bytes"], details["sha256"]) != expected:
                    raise ValueError(f"redistributable member size or SHA-256 mismatch: {name}")
                runtime_files[name] = extracted / name
                redist_source_members.append(name)
        for output_name, license_path in runtime_licenses.items():
            if not license_path.is_file():
                raise FileNotFoundError(license_path)
            runtime_files[output_name] = license_path

        runtime_filename = "runtime-b8696-win-cpu-x64-r2.zip"
        model_filename = "granite-4.0-h-350m-q8-0.zip"
        runtime_record = deterministic_zip(output_dir / runtime_filename, runtime_files)
        model_record = deterministic_zip(
            output_dir / model_filename,
            {MODEL_SOURCE: model_input, "LICENSE-Apache-2.0.txt": apache_license},
        )

    runtime_files_record = runtime_record.pop("files")
    model_files_record = model_record.pop("files")
    return {
        "format_version": 2,
        "release": {
            "repo": "Max/teammanager-models",
            "runtime_tag": RUNTIME_RELEASE_TAG,
            "runtime_state": "prepared-not-published",
            "runtime_download_base_url": RUNTIME_RELEASE_BASE,
            "model_tag": MODEL_RELEASE_TAG,
            "model_state": "published-immutable",
            "model_download_base_url": MODEL_RELEASE_BASE,
        },
        "packages": [
            {
                "ID": "llama-cpp-b8696-win-cpu-x64-r2",
                "ArchiveURL": f"{RUNTIME_RELEASE_BASE}/{runtime_filename}",
                "ArchiveSizeBytes": runtime_record["archive_size_bytes"],
                "ArchiveSHA256": runtime_record["archive_sha256"],
                "Files": [
                    {"Name": name, "SizeBytes": details["size_bytes"], "SHA256": details["sha256"]}
                    for name, details in runtime_files_record.items()
                ],
            },
            {
                "ID": "granite-4.0-h-350m-q8-0",
                "ArchiveURL": f"{MODEL_RELEASE_BASE}/{model_filename}",
                "ArchiveSizeBytes": model_record["archive_size_bytes"],
                "ArchiveSHA256": model_record["archive_sha256"],
                "Files": [
                    {"Name": name, "SizeBytes": details["size_bytes"], "SHA256": details["sha256"]}
                    for name, details in model_files_record.items()
                ],
            },
        ],
        "sources": {
            "runtime": {
                "url": RUNTIME_SOURCE_URL,
                "tag": "b8696",
                "commit": RUNTIME_SOURCE_COMMIT,
                "archive_size_bytes": RUNTIME_SOURCE_SIZE,
                "archive_sha256": RUNTIME_SOURCE_SHA256,
                "selected_upstream_members": sorted(runtime_source_members),
                "license_files": [
                    {
                        "archive_name": output_name,
                        "source_path": source_name,
                        "source_url": source_url,
                        "sha256": expected_sha256,
                    }
                    for output_name, (source_name, expected_sha256, source_url) in sorted(RUNTIME_LICENSES.items())
                ],
            },
            "redistributable_runtime": {
                "url": REDIST_SOURCE_URL,
                "release_tag": "moonshine-v0.1.5",
                "source_revision": REDIST_SOURCE_REVISION,
                "archive_size_bytes": REDIST_SOURCE_SIZE,
                "archive_sha256": REDIST_SOURCE_SHA256,
                "file_version": REDIST_VERSION,
                "selected_source_members": sorted(redist_source_members),
                "license_terms_url": "https://visualstudio.microsoft.com/license-terms/",
                "redistribution_url": "https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution",
            },
            "model": {
                "repo": MODEL_SOURCE_REPO,
                "revision": MODEL_SOURCE_REVISION,
                "file": MODEL_SOURCE,
                "url": MODEL_SOURCE_URL,
                "size_bytes": MODEL_SOURCE_SIZE,
                "sha256": MODEL_SOURCE_SHA256,
                "base_model_repo": "ibm-granite/granite-4.0-h-350m",
                "license": "Apache-2.0",
                "license_url": "https://www.apache.org/licenses/LICENSE-2.0.txt",
                "conversion_provenance": "IBM's pinned GGUF repository README says the repository contains GGUF conversions of the IBM Granite base model; it does not state the conversion tool version or command.",
                "apache_license_sha256": APACHE_LICENSE_SHA256,
            },
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=ROOT.parent / "artifacts/generative-radio")
    parser.add_argument("--out", type=Path, default=ROOT.parent / "artifacts/managed-radio-assets")
    args = parser.parse_args()
    metadata = build(args.sources, args.out)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "provenance.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
