# Alpha build inputs

These immutable Forgejo release assets are the only model/runtime inputs for
the first private TeamManager Alpha. Race Engineer copies the five **required**
inputs into its complete Windows installer. It knows the one **optional** input
only for an explicit, user-confirmed download. URLs, sizes, and hashes below
were recorded from the Forgejo releases on 2026-08-02.

| Class | ID | Immutable URL | Size (bytes) | SHA-256 | Licence and upstream provenance |
| --- | --- | --- | ---: | --- | --- |
| Required | `pocket-runtime` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-v2.1.0-r3/pocket-runtime-win-cpu-v2.1.0-r3.zip` | 306398674 | `b6994cfc4fa48799c59473378baf0e228265cd4562ee61890615ac66b4df4713` | MIT and bundled upstream dependency licences. TeamManager Windows CPU package of [Kyutai Pocket TTS](https://github.com/kyutai-labs/pocket-tts), model revision `39592ff23c9ef80098bb74895d104c26275fe2c9`. |
| Required | `pocket-english` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-v2.1.0/pocket-model-en-v2.1.0.zip` | 219090877 | `97889ede2dad2f82dbcabe2e52cca4544fefb4cfb1ae5a201e7e69b15e87bcf5` | CC-BY-4.0 with upstream model-card terms. Kyutai Pocket TTS English model, revision `39592ff23c9ef80098bb74895d104c26275fe2c9`. |
| Required | `pocket-alba` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-v2.1.0-r3/pocket-voice-alba-v2.1.0-r3.zip` | 6195421 | `53dee14d891fe666e35151511888ca7281582c8c55268a02b2181220881a7f1d` | CC0-1.0 catalog voice state. Official Kyutai Pocket TTS Alba voice, immutable upstream revision `e041936c75475d350b405bc870bcf7c22da4e9e6`. |
| Required | `whisper-runtime` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/whispercpp-v1.9.1/teammanager-whisper-runtime-only-win-x64-v1.9.1.zip` | 4505044 | `6ac6eecf51eb0e84bf091bc06d7c2dbb700fef3e4b4e38bb6de1b852b47ba0b6` | MIT; see `LICENSES/whisper.cpp-MIT.txt`. TeamManager runtime-only package of [ggml-org/whisper.cpp v1.9.1](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.1), upstream archive SHA-256 `7d8be46ecd31828e1eb7a2ecdd0d6b314feafd82163038ab6092594b0a063539`. |
| Required | `whisper-base-q5_1` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/whisper-q5-v1/ggml-base-q5_1.bin` | 59707625 | `422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898` | MIT; see `LICENSES/openai-whisper-MIT.txt`. Immutable q5_1 mirror of the OpenAI Whisper base model, converted for whisper.cpp from [ggerganov/whisper.cpp revision `5359861c739e955e79d9a303bcbc70fb988958b1`](https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1). |
| Optional | `whisper-small-q5_1` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/whisper-q5-v1/ggml-small-q5_1.bin` | 190085487 | `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb` | MIT; see `LICENSES/openai-whisper-MIT.txt`. Immutable q5_1 mirror of the OpenAI Whisper small model, converted for whisper.cpp from [ggerganov/whisper.cpp revision `5359861c739e955e79d9a303bcbc70fb988958b1`](https://huggingface.co/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1). |

## License material

The runtime ZIP does **not** contain `whispercpp-LICENSE`. The installer build
copies the separate Forgejo asset into its attribution material:

- `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/whispercpp-v1.9.1/whispercpp-LICENSE`
  — 1078 bytes, SHA-256
  `94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d`;
  this is byte-identical to whisper.cpp v1.9.1's authoritative MIT license and
  is retained as `LICENSES/whisper.cpp-MIT.txt`.
- `LICENSES/openai-whisper-MIT.txt` is the authoritative OpenAI Whisper MIT
  license from [openai/whisper commit `5f86d1d86363843179951550570367b37c5d6f78`](https://github.com/openai/whisper/blob/5f86d1d86363843179951550570367b37c5d6f78/LICENSE),
  1063 bytes, SHA-256
  `b5d65a59060e68c4ff940e1eddfa6f94b2d68fdf58ed7f4dd57721c997e35e9d`.

No other release asset is a first-Alpha dependency. In particular, historical
Pocket language packs, non-Alba voices, Whisper manifest or authority files,
and any Whisper model other than the explicitly selected optional
`whisper-small-q5_1` must not be selected, fetched, or interpreted by the
Alpha runtime. The optional Small input may be downloaded only after explicit
user action; it is never fetched or selected automatically.

Current Race Engineer `main` does not list Natural Radio assets in its closed
`build/alpha-models.lock.json`. Historical Models release records therefore do
not make Natural Radio a current installer input or runtime authority.

## Natural Radio release record

`natural-radio-qwen3-0.6b-dev.1` is an immutable development release. It is
not an Alpha installer input until Race Engineer pins an approved release in
its closed build-input lock.

The release's Q4_K_M GGUF is
`race-engineer-qwen3-0.6b-q4_k_m.gguf` (396,705,632 bytes, SHA-256
`3a627f406fff3e6e1c5fe2d6104f28ef760a6599b4cab31c4bc1c03ae2bf95ff`).
The corresponding Windows runtime archive is
`natural-radio-runtime.zip` (18,990,303 bytes, SHA-256
`810d5c228cde848ed8df4f509676d79974eb0a13c64b88696dc997beaf51f5a`),
containing `llama-server.exe` (SHA-256
`c932a2ac50dbdc5768399723e2e6e6295f7abcdf5243220729022c38ae2c415a`).

The release owner attests that this GGUF is the completed trained Natural
Radio model. That attestation is not a replacement for the listed artifact
fingerprints. For the private Alpha, the owner has explicitly accepted this
attestation instead of an independent reconstruction of the training-to-GGUF
lineage; this record does not claim that such reconstruction was performed.
The model is based on Qwen3 0.6B and is distributed under the Apache License
2.0; see `LICENSES/Qwen3-Apache-2.0.txt`. The local Windows
llama.cpp components are distributed under the MIT License; see
`LICENSES/llama.cpp-MIT.txt`. The runtime archive also contains the signed
LLVM OpenMP binary `libomp140.x86_64.dll`. Its applicable Apache 2.0 with LLVM
Exceptions notice is retained as
`LICENSES/LLVM-20.1.8-Apache-2.0-with-LLVM-exception.txt` (upstream
`llvmorg-20.1.8` original-download SHA-256
`8d85c1057d742e597985c7d4e6320b015a9139385cff4cbae06ffc0ebe89afee`; the
retained text omits only the upstream terminal blank line).
Any later immutable Natural Radio release must retain all applicable notices
with its installer-owned assets.

`docs/natural-radio-d1-gold.md` and its retained JSON result record the fixed,
repeatable model-and-runtime Gold evaluation for these exact development
fingerprints. It is a model-side Windows result, not D2 integration evidence or
a substitute for the still-pending Windows VM criterion.
