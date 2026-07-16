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

## Managed Whisper authority

`scripts/publish-whisper-authority.py` is the producer for managed Whisper's
closed `teammanager-managed-whisper-authority-v1` release object. It validates
the already-published schema-v3 manifest, runtime-only archive, and
`base-q5_1` bytes; signs the Whisper-specific domain plus exact JSON bytes with
Ed25519; self-verifies the raw 64-byte signature; and emits a lowercase SHA-256
sidecar. Forgejo is canonical and the GitHub URLs in the authority are a
byte-identical, fully verified fallback only.

Publication validates every runtime ZIP member against the schema-v3 inventory,
pins the reviewed input sizes and SHA-256 values in the producer, then validates
the final JSON/signature/sidecar tuple again. The checked-in
authority is generated from Forgejo releases `whispercpp-v1.9.1` and
`whisper-q5-v1`; it does not authorize the older full runtime archive or any
optional model. To perform the same offline validation after downloading the
three pinned inputs:

```sh
python3 scripts/publish-whisper-authority.py \
  --validate-authority whisper-authority/teammanager-whisper-authority-v1.json \
  --signature whisper-authority/teammanager-whisper-authority-v1.json.sig \
  --sidecar whisper-authority/teammanager-whisper-authority-v1.json.sha256 \
  --release-manifest /path/to/teammanager-whisper-runtime-only-win-x64-v1.9.1.manifest-v3.json \
  --runtime /path/to/teammanager-whisper-runtime-only-win-x64-v1.9.1.zip \
  --model /path/to/ggml-base-q5_1.bin \
  --public-key /path/to/teammanager-model-manifest-ed25519.pub
```

The Ed25519 signed message is the ASCII domain
`TeamManager managed Whisper authority v1`, one NUL byte, and the exact JSON
bytes. The `.sig` file is raw 64-byte Ed25519 output; the `.sha256` file is one
lowercase hex digest plus LF. Tests are offline and use temporary fixture keys
and archives only: `python3 -m unittest scripts/test_publish_whisper_authority.py`.

No production private key is stored here. The Forgejo workflow reads it only
from the model-manifest signing secret. Test keys exist only inside deterministic
unit-test temporary directories and cannot activate TeamManager release code.
