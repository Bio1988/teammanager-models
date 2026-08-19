"""Fail closed when the reviewed Alpha voice contract is incomplete or drifts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "alpha-voice-contract.md"


def require(document: str, value: str) -> None:
    if " ".join(value.split()) not in " ".join(document.split()):
        raise AssertionError(f"missing reviewed voice-contract value: {value}")


def main() -> None:
    document = CONTRACT.read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

    require(document, "Race Engineer owns runtime voice selection.")
    require(document, "Charles is the default.")
    require(document, "**not release-ready**")
    require(document, "Do not alter the historical `manifest.json` to represent these voices.")
    require(document, "**not Alpha eligible**")

    revision = "323332d33f997de8394f24a193e1a76df720e01a"
    voices = (
        (
            "pocket-voice-charles",
            "p254_023_enhanced.wav",
            "charles.wav",
            "639272",
            "6b681a429198f16e378d53bccb08d06939da7b00144a7696111d4f8f76be7756",
        ),
        (
            "pocket-voice-michael",
            "p360_023_enhanced.wav",
            "michael.wav",
            "751140",
            "b6743e9195e5e3fd34fe9d1633ae93f7ffab787b249e45f6467d7d6f7a6ee6ad",
        ),
        (
            "pocket-voice-eve",
            "p361_023_enhanced.wav",
            "eve.wav",
            "671872",
            "396e7cbd066b0f3fb6d67fa26e7904076958239d736d4390f15b5fe88feb14cd",
        ),
    )
    for voice_id, source_file, installed_file, size, digest in voices:
        require(document, voice_id)
        require(document, f"/resolve/{revision}/vctk/{source_file}")
        require(document, f"pocket/voice/{installed_file}")
        require(document, size)
        require(document, digest)

    for value in (
        "CC-BY-4.0",
        "Kyutai and the VCTK source dataset",
        "natural-radio-runtime",
        "810d5c228c2de848ed8df4f509676d79974eb0a13c64b88696dc997beaf51f5a",
        "natural-radio-model",
        "3a627f406fff3e6e1c5fe2d6104f28ef760a6599b4cab31c4bc1c03ae2bf95ff",
    ):
        require(document, value)

    historical_assets = manifest["assets"]["pocket_bundles"]["default_windows"]
    if historical_assets["catalog_voice"]["id"] != "kyutai__pocket-voice-alba":
        raise AssertionError("historical Pocket R3 provenance unexpectedly changed")
    if "charles" in json.dumps(manifest, sort_keys=True).lower():
        raise AssertionError("historical manifest must not become a stock-voice authority")


if __name__ == "__main__":
    main()
