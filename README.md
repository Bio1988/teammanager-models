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
