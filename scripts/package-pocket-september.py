#!/usr/bin/env python3
"""Repackage the pinned September 2026 Pocket English export deterministically."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SIZE = 207273014
SOURCE_SHA256 = "8a3dffbca1d7c33a41f312173e08a7df69df7f0e2b2ac6f494fb4d4e842cd9aa"
SOURCE_ROOT = "pocket/experimental/english-2026-09"
MANIFEST_MEMBER = f"{SOURCE_ROOT}/model.json"
INPUT_TO_OUTPUT = {
    f"{SOURCE_ROOT}/cpp/flow_lm_flow.onnx": "cpp/flow_lm_flow.onnx",
    f"{SOURCE_ROOT}/cpp/flow_lm_main.onnx": "cpp/flow_lm_main.onnx",
    f"{SOURCE_ROOT}/cpp/mimi_decoder.onnx": "cpp/mimi_decoder.onnx",
    f"{SOURCE_ROOT}/cpp/mimi_encoder.onnx": "cpp/mimi_encoder.onnx",
    f"{SOURCE_ROOT}/cpp/text_conditioner.onnx": "cpp/text_conditioner.onnx",
    f"{SOURCE_ROOT}/weights/tokenizer.model": "weights/tokenizer.model",
}
SOURCE_MEMBER_SIZES = {
    f"{SOURCE_ROOT}/cpp/flow_lm_flow.onnx": 39081890,
    f"{SOURCE_ROOT}/cpp/flow_lm_main.onnx": 302364908,
    f"{SOURCE_ROOT}/cpp/mimi_decoder.onnx": 41413208,
    f"{SOURCE_ROOT}/cpp/mimi_encoder.onnx": 39264745,
    f"{SOURCE_ROOT}/cpp/text_conditioner.onnx": 16388309,
    MANIFEST_MEMBER: 902,
    f"{SOURCE_ROOT}/weights/tokenizer.model": 59339,
}
NOTICE_PATH = ROOT / "docs/pocket-english-september-2026-notice.md"
LICENSE_PATH = ROOT / "LICENSES/CC-BY-4.0.txt"
LICENSE_MEMBER = "LICENSES/CC-BY-4.0.txt"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_member_path(name):
    path = PurePosixPath(name)
    if (
        not name
        or "\x00" in name
        or "\\" in name
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in name.split("/"))
    ):
        raise ValueError(f"unsafe ZIP member path: {name!r}")


def checked_source(path):
    if path.stat().st_size != SOURCE_SIZE or sha256_file(path) != SOURCE_SHA256:
        raise ValueError("source archive size or SHA-256 does not match the pinned export")

    with zipfile.ZipFile(path) as source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        for info in infos:
            check_member_path(info.filename)
            mode = stat.S_IFMT(info.external_attr >> 16)
            if info.is_dir() or mode not in (0, stat.S_IFREG) or info.flag_bits & 1:
                raise ValueError(f"unsupported ZIP member: {info.filename!r}")
        expected_names = {MANIFEST_MEMBER, *INPUT_TO_OUTPUT}
        if len(names) != len(set(names)) or set(names) != expected_names:
            raise ValueError("source archive inventory does not match the pinned export")
        if any(info.file_size != SOURCE_MEMBER_SIZES[info.filename] for info in infos):
            raise ValueError("source archive member sizes do not match the pinned export")
        manifest = json.loads(source.read(MANIFEST_MEMBER))
        expected_graphs = {
            name[len(SOURCE_ROOT) + 1 :]
            for name, target in INPUT_TO_OUTPUT.items()
            if target.startswith("cpp/")
        }
        graph_hashes = {item["path"]: item["sha256"] for item in manifest["cpp_models"]}
        if set(graph_hashes) != expected_graphs or len(graph_hashes) != len(manifest["cpp_models"]):
            raise ValueError("model.json graph inventory does not match the export")
        expected_hashes = {
            f"{SOURCE_ROOT}/{relative}": digest
            for relative, digest in graph_hashes.items()
        }
        expected_hashes[f"{SOURCE_ROOT}/weights/tokenizer.model"] = manifest["tokenizer_sha256"]

        for source_name in INPUT_TO_OUTPUT:
            digest = hashlib.sha256()
            with source.open(source_name) as member:
                for chunk in iter(lambda: member.read(1 << 20), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_hashes[source_name]:
                raise ValueError(f"model.json SHA-256 mismatch: {source_name}")
    return {
        output_name: expected_hashes[source_name]
        for source_name, output_name in INPUT_TO_OUTPUT.items()
    }


def package(source_path, output_path, notice_path=NOTICE_PATH, license_path=LICENSE_PATH):
    source_path = Path(source_path)
    output_path = Path(output_path)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("output path must differ from source archive")
    expected = checked_source(source_path)
    additions = {
        "NOTICE.md": Path(notice_path).read_bytes(),
        LICENSE_MEMBER: Path(license_path).read_bytes(),
    }
    expected.update({name: sha256(data) for name, data in additions.items()})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial = output_path.with_name(output_path.name + ".partial")
    try:
        with zipfile.ZipFile(source_path) as source, zipfile.ZipFile(
            partial, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as bundle:
            output_by_source = {output: source_name for source_name, output in INPUT_TO_OUTPUT.items()}
            for name in sorted(expected):
                check_member_path(name)
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                if name in additions:
                    bundle.writestr(info, additions[name], compresslevel=9)
                    continue
                digest = hashlib.sha256()
                with source.open(output_by_source[name]) as input_member, bundle.open(
                    info, "w", force_zip64=True
                ) as output_member:
                    for chunk in iter(lambda: input_member.read(1 << 20), b""):
                        digest.update(chunk)
                        output_member.write(chunk)
                if digest.hexdigest() != expected[name]:
                    raise ValueError(f"source changed while packaging: {name}")
        with zipfile.ZipFile(partial) as bundle:
            if bundle.testzip() or set(bundle.namelist()) != set(expected):
                raise ValueError("generated ZIP failed inventory or CRC verification")
            member_records = {}
            for name, want_hash in expected.items():
                digest = hashlib.sha256()
                with bundle.open(name) as member:
                    for chunk in iter(lambda: member.read(1 << 20), b""):
                        digest.update(chunk)
                if digest.hexdigest() != want_hash:
                    raise ValueError(f"generated ZIP readback mismatch: {name}")
                member_records[name] = {
                    "size_bytes": bundle.getinfo(name).file_size,
                    "sha256": want_hash,
                }
        partial.replace(output_path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    return {
        "archive": {
            "size_bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
        },
        "members": dict(sorted(member_records.items())),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="verified experiment ZIP")
    parser.add_argument("--out", required=True, help="output immutable release ZIP")
    args = parser.parse_args()
    print(json.dumps(package(args.input, args.out), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
