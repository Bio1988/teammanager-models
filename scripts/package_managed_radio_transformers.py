#!/usr/bin/env python3
"""Build the two deterministic pure-transformer managed-radio model ZIPs (Granite 4.0 350M, Gemma 3 270M IT)."""
import argparse
import json
from pathlib import Path

from package_managed_radio_assets import ROOT, deterministic_zip, sha256_file, verify_source

RELEASE_ROOT = "https://forgejo.g-grp.com/Max/teammanager-models/releases/download"
APACHE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"

# id, tag, zip name, gguf name, gguf size, gguf sha256, HF repo, HF revision, extra license files (archive name -> LICENSES/ name)
MODELS = (
    {
        "id": "granite-4.0-350m-q8-0",
        "tag": "managed-radio-granite-4-0-350m-r1",
        "zip": "granite-4.0-350m-q8-0.zip",
        "gguf": "granite-4.0-350m-Q8_0.gguf",
        "size": 378_138_016,
        "sha256": "9595dafb4ed15aa02512c8ea26188744192a6f09530eae0a2747bd3ada96cd36",
        "repo": "ibm-granite/granite-4.0-350m-GGUF",
        "revision": "b8208a86a58427e1739265318028eb5895b74bf2",
        "licenses": {"LICENSE-Apache-2.0.txt": ("Apache-2.0.txt", APACHE_SHA256)},
    },
    {
        "id": "gemma-3-270m-it-q8-0",
        "tag": "managed-radio-gemma-3-270m-it-r1",
        "zip": "gemma-3-270m-it-q8-0.zip",
        "gguf": "gemma-3-270m-it-Q8_0.gguf",
        "size": 291_545_600,
        "sha256": "0ef57d2c838458a1952664260dcba38e5bdda37494f3af732f06e4add24068e3",
        "repo": "ggml-org/gemma-3-270m-it-GGUF",
        "revision": "e7647be17ae1108f2f605ed061ca0608b171afff",
        "licenses": {
            "LICENSE-Gemma-Terms-of-Use.txt": ("Gemma-Terms-of-Use-2026-04-01.txt", None),
            "LICENSE-Gemma-Prohibited-Use-Policy.txt": ("Gemma-Prohibited-Use-Policy-2024-02-21.txt", None),
            "NOTICE": ("NOTICE-Gemma.txt", None),
        },
    },
)


def build(source_dir, out_dir):
    packages = []
    for model in MODELS:
        files = {model["gguf"]: verify_source(Path(source_dir) / model["gguf"], model["size"], model["sha256"])}
        for name, (source, expected) in model["licenses"].items():
            path = ROOT / "LICENSES" / source
            if expected and sha256_file(path) != expected:
                raise ValueError(f"license SHA-256 mismatch: {source}")
            files[name] = path
        record = deterministic_zip(Path(out_dir) / model["zip"], files)
        packages.append({
            "ID": model["id"],
            "ReleaseTag": model["tag"],
            "ArchiveURL": f"{RELEASE_ROOT}/{model['tag']}/{model['zip']}",
            "ArchiveSizeBytes": record["archive_size_bytes"],
            "ArchiveSHA256": record["archive_sha256"],
            "Files": [{"Name": n, "SizeBytes": d["size_bytes"], "SHA256": d["sha256"]} for n, d in record["files"].items()],
            "Source": {
                "repo": model["repo"],
                "revision": model["revision"],
                "url": f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{model['gguf']}",
                "size_bytes": model["size"],
                "sha256": model["sha256"],
            },
        })
    return {"format_version": 1, "packages": packages}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    metadata = build(args.sources, args.out)
    (args.out / "provenance.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
