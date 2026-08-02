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
| Required | `whisper-runtime` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/whispercpp-v1.9.1/teammanager-whisper-runtime-only-win-x64-v1.9.1.zip` | 4505044 | `6ac6eecf51eb0e84bf091bc06d7c2dbb700fef3e4b4e38bb6de1b852b47ba0b6` | MIT; included `whispercpp-LICENSE`. TeamManager runtime-only package of [ggml-org/whisper.cpp v1.9.1](https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.1), upstream archive SHA-256 `7d8be46ecd31828e1eb7a2ecdd0d6b314feafd82163038ab6092594b0a063539`. |
| Required | `whisper-base-q5_1` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/whisper-q5-v1/ggml-base-q5_1.bin` | 59707625 | `422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898` | MIT; TeamManager immutable q5_1 mirror of the [OpenAI Whisper](https://github.com/openai/whisper) base model for whisper.cpp. |
| Optional | `whisper-small-q5_1` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/whisper-q5-v1/ggml-small-q5_1.bin` | 190085487 | `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb` | MIT; TeamManager immutable q5_1 mirror of the [OpenAI Whisper](https://github.com/openai/whisper) small model for whisper.cpp. |

The `whisper-q5-v1` release did not record a distinct upstream conversion
revision for either q5_1 model. Its immutable URL, byte size, and SHA-256 above
are therefore the retained provenance boundary for those packaged artifacts.

No other release asset is a first-Alpha dependency. In particular, historical
Pocket language packs, non-Alba voices, Whisper manifest/authority files, and
larger Whisper models must not be selected, fetched, or interpreted by the
Alpha runtime.
