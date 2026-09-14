#!/usr/bin/env python3
"""Package the three Alpha 31 Moonshine streaming model archives.

Downloads the pinned quantized_26_08_21 files from download.moonshine.ai,
verifies every file by byte size and SHA-256, and writes one deterministic ZIP
per model with the eight files at the archive root. The output bytes are what
the TeamManager Forgejo release publishes; the printed size and SHA-256 are
pinned in race-engineer-go's closed model catalog.

Usage:
    python scripts/package-moonshine-models.py --out <directory>

The eight files per model and their measured SHA-256 values come from the
upstream v0.1.5 catalog (commit
234f60faa0eb388b01cdf7e60aca232af37aefda). Re-running this script against the
same upstream bytes reproduces the archives.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile

BASE = "https://download.moonshine.ai/model"
CATALOG = "quantized_26_08_21"

MODELS = {
    "tiny-streaming-en": {
        "archive": "moonshine-tiny-streaming-en-quantized_26_08_21-r1.zip",
        "files": {
            "adapter.ort": (1319664, "22ecc949e146c49667fda28d102d4e30749a107dc88a396292aa8f277ef1347c"),
            "cross_kv.ort": (1287544, "143a36667b8d05fd9d04e8c337b7ee121f37ef299aea6b3d82bdb3d3401950b4"),
            "decoder_kv.ort": (32583720, "8852553f312adb6c9aa4d17418015049b30f412209ee569d336548c0044627de"),
            "encoder.ort": (7675440, "a8414e1a5dedf9f2093d7680601dd8a9b0433e7020260eafe0e370ead91134ca"),
            "frontend.model.ort": (23344, "5121b561417b638afce0c6c31b760e37c93cf97f80d9b0031aad1fe7b6f25d61"),
            "frontend.weights.ort": (2093464, "217da24ac6f522ebf02da8ef288e77d1ac68d50d4a6821433182e4fbf4204bbd"),
            "streaming_config.json": (509, "74fe5ddebd63b17caf59e8a3b18c17547ff7bce1642050edbb1c3962674f8950"),
            "tokenizer.bin": (249974, "6884b35fd6377d4c4d32336a0bc152f36b64d1e45b6503683cdc238250a8472d"),
        },
    },
    "small-streaming-en": {
        "archive": "moonshine-small-streaming-en-quantized_26_08_21-r1.zip",
        "files": {
            "adapter.ort": (2870368, "c665f742364febad597cc9ac1e0b341ffbee0e24a1466e2f3bde95e6e4771762"),
            "cross_kv.ort": (5356536, "e2d3417144e9514055ebfefe8dcc4c0a55a55adcb8530435844c75c53e352bf6"),
            "decoder_kv.ort": (81878600, "1a05465b1dd955858dfcbee039c0020fb5dd982b0f5094c34e61735d518d771b"),
            "encoder.ort": (44148576, "2d4d973e91e8aca08c51e7e7efa28a46ab265b63d809d5294d18b86bcd85b993"),
            "frontend.model.ort": (26944, "09b1210ae30dc5f0f3e45f0ebab914c254741323114f53fbbe5ae62cca35058f"),
            "frontend.weights.ort": (7769464, "7ef97521bd4bad3928f5bb6808586f4fcc6e92bd5990394112eed7d4052ec338"),
            "streaming_config.json": (512, "26f02b6afb22d60871a5efd85c3d38e569cc0ddb6c5eb6e93d3260152ae8a47a"),
            "tokenizer.bin": (249974, "6884b35fd6377d4c4d32336a0bc152f36b64d1e45b6503683cdc238250a8472d"),
        },
    },
    "medium-streaming-en": {
        "archive": "moonshine-medium-streaming-en-quantized_26_08_21-r1.zip",
        "files": {
            "adapter.ort": (3651296, "3f2a287def57cc094367a0eec3c4f5fc36a32ec420e86764b696920991b20281"),
            "cross_kv.ort": (11643776, "642f6e21cd305be79342207c6f9e6b681d469d55bc48c72b27b84846fb71fd1e"),
            "decoder_kv.ort": (146972408, "193bb366492b74fc4ad338c6778e8d8eb916aaa11b5aa264f9057f4db7759486"),
            "encoder.ort": (94705376, "12915e76ebac7dd287c5ea63965d06103a53ba1ce242a4a34f318f3958c60c37"),
            "frontend.model.ort": (28720, "95768855c70c8251eeecc05fedf69999da1b8ab16f605c9f457fd3354b0ad6b5"),
            "frontend.weights.ort": (11889560, "5ac941f490cbe035b335b99a414cc393d62d4c6f9f2423495b286870d271d709"),
            "streaming_config.json": (513, "28e83b7a28e91472692a035e0dae3116422ae43aeb2bef5ed822c44ce89b88af"),
            "tokenizer.bin": (249974, "6884b35fd6377d4c4d32336a0bc152f36b64d1e45b6503683cdc238250a8472d"),
        },
    },
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(model, name, destination):
    want_size, want_hash = MODELS[model]["files"][name]
    target = os.path.join(destination, model, name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.exists(target) and os.path.getsize(target) == want_size and sha256(target) == want_hash:
        return target
    url = f"{BASE}/{model}/{CATALOG}/{name}"
    partial = target + ".partial"
    for attempt in range(4):
        subprocess.run(["curl", "-fsSL", "--retry", "2", "--max-time", "600", "-o", partial, url], check=True)
        if os.path.getsize(partial) == want_size and sha256(partial) == want_hash:
            os.replace(partial, target)
            return target
        print(f"verify failed (attempt {attempt + 1}): {model}/{name}", file=sys.stderr)
        os.remove(partial)
    raise SystemExit(f"unable to fetch verified {model}/{name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="output directory for the model ZIPs")
    parser.add_argument("--cache", default="", help="optional download cache directory")
    args = parser.parse_args()
    cache = args.cache or os.path.join(args.out, "cache")
    os.makedirs(args.out, exist_ok=True)
    records = {}
    for model, spec in MODELS.items():
        names = sorted(spec["files"])
        paths = [fetch(model, name, cache) for name in names]
        archive = os.path.join(args.out, spec["archive"])
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for path, name in zip(paths, names):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(path, "rb") as handle:
                    bundle.writestr(info, handle.read())
        records[spec["archive"]] = {"size_bytes": os.path.getsize(archive), "sha256": sha256(archive), "model": model}
        print(json.dumps({spec["archive"]: records[spec["archive"]]}, sort_keys=True))
    with open(os.path.join(args.out, "moonshine-model-records.json"), "w") as handle:
        json.dump(records, handle, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
