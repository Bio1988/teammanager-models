# Alpha build inputs

## Current Alpha-4 inventory

Race Engineer's closed `build/alpha-models.lock.json` is the build-input
authority. The current lock has nine required installer inputs and two
optional downloads. The URLs, sizes, SHA-256 values, targets, and classifications
below match that lock.

| Class | ID | Immutable URL | Install target | Size (bytes) | SHA-256 | Licence and upstream provenance |
| --- | --- | --- | --- | ---: | --- | --- |
| Required | `pocket-english` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-english-2026-09-onnx-r1/pocket-tts-english-2026-09-onnx-r1.zip` | `pocket/model` | 207279132 | `4461e94535d8ded09032ec778e774c16f6264ab4b9e49168fdf06ddd38f992ce` | The upstream [Kyutai Pocket TTS model](https://huggingface.co/kyutai/pocket-tts) is marked CC BY 4.0. Source pins, exporter evidence, and deterministic packaging are recorded in the [September package provenance](#pocket-english-september-2026-native-model-package) below. |
| Required | `pocket-voice-charles` | `https://huggingface.co/kyutai/tts-voices/resolve/323332d33f997de8394f24a193e1a76df720e01a/vctk/p254_023_enhanced.wav` | `pocket/voice/charles.wav` | 639272 | `6b681a429198f16e378d53bccb08d06939da7b00144a7696111d4f8f76be7756` | Enhanced VCTK recording (`p254_023_enhanced.wav`), pinned to Kyutai `tts-voices` commit `323332d33f997de8394f24a193e1a76df720e01a`; CC BY 4.0. |
| Required | `pocket-voice-michael` | `https://huggingface.co/kyutai/tts-voices/resolve/323332d33f997de8394f24a193e1a76df720e01a/vctk/p360_023_enhanced.wav` | `pocket/voice/michael.wav` | 751140 | `b6743e9195e5e3fd34fe9d1633ae93f7ffab787b249e45f6467d7d6f7a6ee6ad` | Enhanced VCTK recording (`p360_023_enhanced.wav`), pinned to Kyutai `tts-voices` commit `323332d33f997de8394f24a193e1a76df720e01a`; CC BY 4.0. |
| Required | `pocket-voice-eve` | `https://huggingface.co/kyutai/tts-voices/resolve/323332d33f997de8394f24a193e1a76df720e01a/vctk/p361_023_enhanced.wav` | `pocket/voice/eve.wav` | 671872 | `396e7cbd066b0f3fb6d67fa26e7904076958239d736d4390f15b5fe88feb14cd` | Enhanced VCTK recording (`p361_023_enhanced.wav`), pinned to Kyutai `tts-voices` commit `323332d33f997de8394f24a193e1a76df720e01a`; CC BY 4.0. |
| Required | `moonshine-runtime` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip` | `moonshine/runtime` | 11455945 | `718dca3a95fd02eeb02f483fa750500a51a24576dc099c507de48af154c48335` | Mixed component bundle built from Moonshine v0.1.5, commit `234f60faa0eb388b01cdf7e60aca232af37aefda`; Moonshine and ONNX Runtime MIT notices plus Microsoft VC redistributable terms. The archive has no single umbrella licence; TeamManager helper code remains proprietary under Race Engineer's LICENSE. |
| Required | `moonshine-small-streaming-en` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/moonshine-small-streaming-en-quantized_26_08_21-r1.zip` | `moonshine/small-streaming-en` | 121672393 | `ce697ac0dcf1b5b949b4ba1beba4dd19e2c2042c335e26e620ff28706ef8de00` | English streaming model from Moonshine v0.1.5, commit `234f60faa0eb388b01cdf7e60aca232af37aefda`; MIT. |
| Required | `minilm-model` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/minilm-l6-v2-quint8-avx2-r1/all-MiniLM-L6-v2-quint8-avx2.onnx` | `intent/all-MiniLM-L6-v2-quint8-avx2.onnx` | 23046789 | `b941bf19f1f1283680f449fa6a7336bb5600bdcd5f84d10ddc5cd72218a0fd21` | Based on [Sentence Transformers all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), whose model card specifies Apache 2.0. The exact ONNX conversion revision and recipe are not retained here. |
| Required | `minilm-vocab` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/minilm-l6-v2-quint8-avx2-r1/all-MiniLM-L6-v2-vocab.txt` | `intent/all-MiniLM-L6-v2-vocab.txt` | 231508 | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` | Tokenizer vocabulary for all-MiniLM-L6-v2; Apache 2.0 model distribution. |
| Required | `minilm-license` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/minilm-l6-v2-quint8-avx2-r1/LICENSE-Apache-2.0.txt` | `licenses/minilm-LICENSE-Apache-2.0.txt` | 11358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` | Apache License 2.0 notice packaged alongside the MiniLM model. |
| Optional | `moonshine-tiny-streaming-en` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/moonshine-tiny-streaming-en-quantized_26_08_21-r1.zip` | `moonshine/optional/moonshine-tiny-streaming-en` | 36624898 | `41e1882d3ddc7c8a70778224879c929f9b4d87f77c57e9f031757bb27751e3c5` | English streaming model from Moonshine v0.1.5, commit `234f60faa0eb388b01cdf7e60aca232af37aefda`; MIT. |
| Optional | `moonshine-medium-streaming-en` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/moonshine-medium-streaming-en-quantized_26_08_21-r1.zip` | `moonshine/optional/moonshine-medium-streaming-en` | 236904989 | `d22e9adbb0232db4fcc2d5594d0155965efd47222fccd59cda38dd84f0e07305` | English streaming model from Moonshine v0.1.5, commit `234f60faa0eb388b01cdf7e60aca232af37aefda`; MIT. |

Only the two optional entries may be downloaded after installation, and only
after explicit user action. Required Moonshine Small is packaged with the
installer. No Whisper model is part of this current lock. The `tts-voices`
revision identifies the three VCTK source files; the
[pinned Kyutai voice catalog](https://huggingface.co/kyutai/tts-voices/tree/323332d33f997de8394f24a193e1a76df720e01a/vctk)
and [its README](https://huggingface.co/kyutai/tts-voices/blob/323332d33f997de8394f24a193e1a76df720e01a/README.md)
say VCTK is CC BY 4.0 and enhanced recordings are cleaned versions created
using ai-coustics. The upstream Pocket model card specifies CC BY 4.0. Source
pins, exporter evidence, and deterministic packaging for the September ONNX
package are recorded in the [September package provenance](#pocket-english-september-2026-native-model-package).
The release records the weight, configuration, and tokenizer revisions below;
the ONNX conversion recipe is not retained.
The MiniLM model card specifies Apache 2.0, but this repository does not retain
its exact ONNX conversion revision or recipe. The asset URLs, sizes, and
SHA-256 values above pin the delivered Pocket and MiniLM artifacts. The Pocket
packaging step verified its source archive and model files against its
manifest, but did not re-export weights or verify Windows audio output; the
MiniLM artifact pin does not establish its missing conversion history.
The three VCTK WAVs are a direct-upstream-source exception: this
repository does not mirror them, and this review did not download or rehash the
files. Their availability and exact object bytes therefore remain unverified
here; the lock's full commit, size, and SHA-256 remain the consumer's pins.

## Alpha 5 intent model inputs

Race Engineer's Alpha-5 candidate lock marks the six E5 and MiniLM L12 files
below as required. These records document that candidate and do not change the
current Alpha-4 inventory above. The E5 model and license assets referenced by
the candidate lock are prepared but unpublished. Lock targets are relative to
the model pack root; the installer places that pack under `runtime/`, so
`intent/...` and `licenses/...` are installed as `runtime/intent/...` and
`runtime/licenses/...`.

### Multilingual E5 Small

The source is [`intfloat/multilingual-e5-small` at revision `0e60b8d9d2166d80387f86e3b48ec9ced55f4d15`](https://huggingface.co/intfloat/multilingual-e5-small/blob/0e60b8d9d2166d80387f86e3b48ec9ced55f4d15/README.md). Its pinned model card declares MIT; the repository has no standalone license file. The source FP32 ONNX file [`onnx/model.onnx`](https://huggingface.co/intfloat/multilingual-e5-small/resolve/0e60b8d9d2166d80387f86e3b48ec9ced55f4d15/onnx/model.onnx) is 470268510 bytes, SHA-256 `ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665`.

| ID | Candidate asset/source | Model-pack target | Size (bytes) | SHA-256 | License and provenance |
| --- | --- | --- | ---: | --- | --- |
| `e5-model` | Prepared, unpublished `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/intent-multilingual-e5-small-0e60b8d9-r1/multilingual-e5-small-quint8.onnx` | `intent/multilingual-e5-small-quint8.onnx` | 118330479 | `c9391bd927dbf1aadedde96db8ad660034be110d04de4eb4ee6ec323d5dab618` | MIT; per-channel generic QUInt8 derived from the pinned FP32 source. |
| `e5-tokenizer` | [Pinned SentencePiece file](https://huggingface.co/intfloat/multilingual-e5-small/resolve/0e60b8d9d2166d80387f86e3b48ec9ced55f4d15/onnx/sentencepiece.bpe.model) | `intent/multilingual-e5-small-sentencepiece.bpe.model` | 5069051 | `cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865` | From the same upstream revision; XLM-R SentencePiece tokenizer. |
| `e5-license` | Prepared, unpublished `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/intent-multilingual-e5-small-0e60b8d9-r1/e5-LICENSE-MIT.txt` | `licenses/e5-LICENSE-MIT.txt` | 1082 | `6e90701309596a0bda99f53196b72144b0e3387a2b5b364a418a79f5b49595ea` | MIT text from [`microsoft/unilm` commit `31c5b904ca1bf2afb4c234a6675c683a4e5fc7cd`](https://github.com/microsoft/unilm/blob/31c5b904ca1bf2afb4c234a6675c683a4e5fc7cd/LICENSE). |

The quantizer is Race Engineer's `scripts/quantize-intent-e5.py` from commit
`730f0ac4f8cfa3f8bf6143d9fe75d19663a270b8`. It uses Python with ONNX Runtime
1.23.2, ONNX 1.19.0 and NumPy 2.5.3, calling `quantize_dynamic` with
`per_channel=True`,
`reduce_range=False`, and `weight_type=QUInt8`. The output is
`multilingual-e5-small-quint8.onnx` above. No ZIP is used: the model and MIT
notice are separate assets in the proposed, unpublished tag
`intent-multilingual-e5-small-0e60b8d9-r1`; the tokenizer stays a direct pinned
Hugging Face file. The runtime uses ONNX Runtime 1.23.2 and `rembed` v0.3.0
(Apache-2.0) for the XLM-R SentencePiece tokenizer, with the existing
`query: ` prefix, masked-mean pooling and L2 normalization.

### MiniLM L12 comparison

The source is [`sentence-transformers/all-MiniLM-L12-v2` at revision `a50ef00143b4d5391434df20ae11632588ac25be`](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2/blob/a50ef00143b4d5391434df20ae11632588ac25be/README.md). The pinned model card declares Apache-2.0. This is an experimental comparison with the existing L6 model; it does not replace the default or establish a safety improvement.

| ID | Pinned source | Model-pack target | Size (bytes) | SHA-256 | License and provenance |
| --- | --- | --- | ---: | --- | --- |
| `minilm-l12-model` | [Quantized AVX2 ONNX](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2/resolve/a50ef00143b4d5391434df20ae11632588ac25be/onnx/model_quint8_avx2.onnx) | `intent/all-MiniLM-L12-v2-quint8-avx2.onnx` | 34160110 | `3c5e33c478496a43413086336955119154d56f3c3d0dccadb484041dc1ce762d` | Apache-2.0; upstream quantized export, no local conversion recipe. |
| `minilm-l12-vocab` | [Vocabulary](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2/resolve/a50ef00143b4d5391434df20ae11632588ac25be/vocab.txt) | `intent/all-MiniLM-L12-v2-vocab.txt` | 231508 | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` | Apache-2.0 model distribution; byte-identical to the existing L6 vocabulary. |
| `minilm-l12-license` | [Existing immutable L6 Apache license asset](https://forgejo.g-grp.com/Max/teammanager-models/releases/download/minilm-l6-v2-quint8-avx2-r1/LICENSE-Apache-2.0.txt) | `licenses/minilm-l12-LICENSE-Apache-2.0.txt` | 11358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` | Canonical Apache-2.0 text, reused without modification. |

The pinned
[`sentence_bert_config.json`](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2/resolve/a50ef00143b4d5391434df20ae11632588ac25be/sentence_bert_config.json)
is 53 bytes, SHA-256
`70f4448f31320443fe3557cacea5abf2dcc4915dda8c80646bec9f3bb0aa5a1f`, and
sets `max_seq_length` to 128. The model card describes truncation beyond 256
word pieces. The existing MiniLM runtime caps input at 64 pieces including
CLS/SEP, and Alpha 5 retains that limit. The upstream model has 384 dimensions
and 33.4 million parameters. Its ONNX file is already quantized; no local
conversion recipe is used. No new Forgejo model release asset or L12-specific
tag has been published.

## Historical first-Alpha inventory

The table below records the first private TeamManager Alpha only. Race Engineer
copied five required inputs into that installer and allowed one optional input
after explicit user confirmation. URLs, sizes, and hashes were recorded from
Forgejo releases on 2026-08-02.

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

No other release asset was a first-Alpha dependency. In particular, historical
Pocket language packs, non-Alba voices, Whisper manifest or authority files,
and any Whisper model other than the explicitly selected optional
`whisper-small-q5_1` were outside that first-Alpha snapshot. The optional Small
input could be downloaded only after explicit user action; it was not fetched
or selected automatically.

## Pocket TTS 3.1.0 release provenance (2026-09-16)

Race Engineer Alpha 2's closed `build/alpha-models.lock.json` is the authority
for installer inputs. This dated record documents assets published in the
`pocket-tts-v3.1.0-r2` prerelease; it does not revise the historical first-Alpha
table or select these assets for an installer.

| Asset | Immutable URL | Size (bytes) | SHA-256 | Licence and upstream provenance |
| --- | --- | ---: | --- | --- |
| Pocket TTS Windows CPU runtime `pocket-runtime-win-cpu-v3.1.0-r2.zip` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-v3.1.0-r2/pocket-runtime-win-cpu-v3.1.0-r2.zip` | 278866753 | `55a11ac8bf1b2662640426aa712f64f6b0551f62d3e7729a1ac35d2c0fcd40ad` | MIT and bundled upstream dependency licences. TeamManager Windows CPU package of Kyutai Pocket TTS 3.1.0, Python 3.11.9 and CPU-only wheels; model revision `39592ff23c9ef80098bb74895d104c26275fe2c9`. It supersedes the never-consumed `pocket-tts-v3.1.0-r1` prerelease, which remains unchanged. |
| Pocket English generation config `pocket-model-en-config-v3.1.0-r1.zip` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-v3.1.0-r2/pocket-model-en-config-v3.1.0-r1.zip` | 739 | `fe5b3e6b7c5be1c73ba43e05476d0c4b0ad23142cf2035423a6fa9221bf2daf9` | CC-BY-4.0 with upstream model-card terms. Pocket TTS 3.1.0 English generation config (`default_temperature: 0.3`) from the pinned `pocket_tts==3.1.0` wheel, with local model-pack weight and tokenizer paths. |

## Alpha 31 Moonshine increment

This section records the Alpha 31 publication and selection history. It does
not describe the current Alpha-4 selection above. At Alpha 31, the runtime and
three English model archives below were published; the then-current installer
selection remained defined by Race Engineer's lock.

The upstream pin is [moonshine-ai/moonshine v0.1.5](https://github.com/moonshine-ai/moonshine/releases/tag/v0.1.5),
annotated tag `bf6ae1590d0928fd704772d0e80d6fef39424be8`, resolving to commit
`234f60faa0eb388b01cdf7e60aca232af37aefda`.

| Alpha 31 class | ID | URL | Publication status | Size (bytes) | SHA-256 | Licence and upstream provenance |
| --- | --- | --- | --- | ---: | --- | --- |
| Alpha 31 required | `moonshine-runtime` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip` | Published immutable Forgejo release asset; canonical URL and full public readback verified. | 11455945 | `718dca3a95fd02eeb02f483fa750500a51a24576dc099c507de48af154c48335` | Component licenses: Moonshine MIT and ONNX Runtime MIT; Microsoft [Visual C++ redistributable terms](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution) for the bundled VC runtime. The ZIP has no single umbrella license. TeamManager helper code remains proprietary under Race Engineer's TeamManager LICENSE; these notices do not reclassify TeamManager helper code. TeamManager Windows x64 helper runtime built from the pinned Moonshine revision. |
| Alpha 31 optional | `moonshine-tiny-streaming-en` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/moonshine-tiny-streaming-en-quantized_26_08_21-r1.zip` | Published immutable Forgejo release asset. | 36624898 | `41e1882d3ddc7c8a70778224879c929f9b4d87f77c57e9f031757bb27751e3c5` | MIT; see `LICENSES/moonshine-MIT.txt`. English streaming model from the pinned Moonshine revision. |
| Alpha 31 optional | `moonshine-small-streaming-en` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/moonshine-small-streaming-en-quantized_26_08_21-r1.zip` | Published immutable Forgejo release asset. | 121672393 | `ce697ac0dcf1b5b949b4ba1beba4dd19e2c2042c335e26e620ff28706ef8de00` | MIT; see `LICENSES/moonshine-MIT.txt`. English streaming model from the pinned Moonshine revision. |
| Alpha 31 optional | `moonshine-medium-streaming-en` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/moonshine-medium-streaming-en-quantized_26_08_21-r1.zip` | Published immutable Forgejo release asset. | 236904989 | `d22e9adbb0232db4fcc2d5594d0155965efd47222fccd59cda38dd84f0e07305` | MIT; see `LICENSES/moonshine-MIT.txt`. English streaming model from the pinned Moonshine revision. |

The runtime archive was published in `moonshine-v0.1.5` and its canonical URL
was verified by a full public readback against the recorded 11,455,945 bytes
and SHA-256. The product owner authorized publication after the recorded local
build and smoke evidence. A clean Windows verification without Visual Studio
remains pending; this record does not claim that criterion. The archive has a
flat root containing the six runtime contract files and `moonshine-MIT.txt`,
`onnxruntime-MIT.txt`; it contains no model weights. The three model archives
each contain exactly the eight pinned `quantized_26_08_21` files. In the
Alpha-31 policy snapshot, these three Moonshine models and Whisper Small were
optional downloads and Whisper Base was the default. Current Alpha-4 marks
Moonshine Small required and Tiny/Medium optional; see the inventory above.

Current Race Engineer `main` does not list Natural Radio assets in its closed
`build/alpha-models.lock.json`. Historical Models release records therefore do
not make Natural Radio a current installer input or runtime authority.

## Pocket English September 2026 native model package

The staged immutable asset is
`https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-english-2026-09-onnx-r1/pocket-tts-english-2026-09-onnx-r1.zip`
(207,279,132 bytes; SHA-256
`4461e94535d8ded09032ec778e774c16f6264ab4b9e49168fdf06ddd38f992ce`).
Race Engineer selects installer inputs through its closed
`build/alpha-models.lock.json`; this record alone does not select an input.

The release archive contains exactly five FP32 ONNX graphs under `cpp/`,
`weights/tokenizer.model`, `NOTICE.md`, and `LICENSES/CC-BY-4.0.txt`. It was
repacked deterministically from the development export
`new-dev-Pocket-English-2026-09-dev-model.zip` (207,273,014 bytes; SHA-256
`8a3dffbca1d7c33a41f312173e08a7df69df7f0e2b2ac6f494fb4d4e842cd9aa`).
The exporter evidence records eleven FP32 comparisons and a Linux native CPU
smoke test; this packaging step verified the source archive and each model
file against its manifest, but did not re-export the weights or verify Windows
audio output.

The source weights are [Kyutai Pocket TTS](https://huggingface.co/kyutai/pocket-tts)
at revision `983151f13aaeab1b13c1e5e3c2c383d49a9edf3f`, with full-clone
weights SHA-256 `fb0dc01b0d4d2e1c905b7a3e0676e3d9c96d5ae460e24e3ab94981805babf997`.
The Pocket TTS v3.3.0 configuration source is commit
`3dbee45d343d7dddd0d105468d17f8dcba14db3e`. The tokenizer came from
[kyutai/pocket-tts-without-voice-cloning](https://huggingface.co/kyutai/pocket-tts-without-voice-cloning/tree/e7205b6ee50e654a5ea19f0e9df2b0813b05e921)
at revision `e7205b6ee50e654a5ea19f0e9df2b0813b05e921`, path
`languages/english_2026-09/tokenizer.model` (59,339 bytes; SHA-256
`d461765ae179566678c93091c5fa6f2984c31bbe990bf1aa62d92c64d91bc3f6`). The model is
identified as CC BY 4.0 with additional upstream model-card use conditions;
the bundled notice and license retain attribution and terms.

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
