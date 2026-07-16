# TeamManager Models

Versioned model artifacts for TeamManager — KoboldCPP, Chatterbox, STT/TTS/LLM models.

## Manifest

`manifest.json` is the installer/runtime dependency catalog used by TeamManager/DRE-Go setup flows.

Top-level asset groups:

- `koboldcpp` — managed KoboldCPP binaries.
- `chatterbox` — managed Chatterbox server payload.
- `models` — single-file STT/TTS/LLM assets that are already exposed as Forgejo release downloads.
- `voice_profiles` — bundled/generated race engineer voice profile metadata.
- `voice_tts_library` — multi-file voice/TTS model dependency catalog for Pocket TTS, NeuTTS, Chatterbox, KokoClone, MOSS, LuxTTS, Sopro, ZipVoice, and archived local X-Voice artifacts.

`voice_tts_library` entries are mirrored locally on the AI-Box under `/opt/ai-box/models/voice-tts-library`. They are catalogued here so the installer/runtime can grow support for snapshot or bundle downloads without relying on memory or ad-hoc paths.

Important: `voice_tts_library` entries are not all single release-asset URLs yet. Existing `models` entries are immediately downloadable release assets; `voice_tts_library` entries describe repository snapshots or local artifacts that must be consumed by snapshot-aware installer code or promoted into release bundles before public installer distribution.

## Pocket clone compatibility authority

`scripts/publish-pocket-model-manifest.py` is the only producer for the closed
`assets.pocket_bundles.default_windows.state_compatibility_model` object. It
derives the English model, config, and cloning-weight SHA-256 values directly
from `pocket-model-en-v2.1.0.zip`, verifies the canonical runtime and Alba
archives, signs the exact versioned manifest bytes with Ed25519, verifies that
detached signature, emits a lowercase manifest SHA-256 sidecar, and only then
emits branch-manifest bytes.

The clone MVP is English-only. Its immutable inputs are the already-published
`pocket-tts-v2.1.0` assets; no additional language archive is an MVP gate. The
incomplete Forgejo release 22 (`pocket-tts-clone-weights-v2.1.0-r1`) is retained
as non-authoritative historical staging and is never read by publication or
desktop activation.

No production private key is stored here. The Forgejo workflow reads it only
from the model-manifest signing secret. Test keys exist only inside deterministic
unit-test temporary directories and cannot activate TeamManager release code.
