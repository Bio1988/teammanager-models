# Moonshine Alpha 31 build inputs

Alpha 31 adds the experimental Moonshine streaming Speech to Text backend to
Race Engineer. This document records the immutable TeamManager release assets
and their upstream provenance. Race Engineer's closed
`build/alpha-models.lock.json` remains the runtime authority; this document is
provenance, not a runtime registry.

Upstream pin: `moonshine-ai/moonshine` **v0.1.5**, annotated tag
`bf6ae1590d0928fd704772d0e80d6fef39424be8` -> commit
`234f60faa0eb388b01cdf7e60aca232af37aefda`.

## Required installer input: Moonshine Windows CPU runtime

The official `moonshine-voice-windows-x86_64.tar.gz` asset (26,109,939 bytes,
SHA-256
`97c1987e8e1cd77bb5fe3b12ce5aad5172637107e1dfda112ea9b21bac8f4b65`)
is a **build input**, not a runnable payload: it ships the static
`lib/moonshine.lib`, headers, and `lib/onnxruntime.dll` (ONNX Runtime
1.23.2), but no Moonshine DLL or executable and no VC runtime.

Race Engineer builds the small helper in
`race-engineer-go/internal/stt/moonshine/native/` against that static SDK and
packages:

| File | Source |
| --- | --- |
| `moonshine-helper.exe` | TeamManager helper built from the pinned static SDK |
| `onnxruntime.dll` | `lib/onnxruntime.dll` from the pinned SDK archive |
| `msvcp140.dll`, `msvcp140_1.dll`, `vcruntime140.dll`, `vcruntime140_1.dll` | MSVC x64 redistributable runtime required by ONNX Runtime and the helper |
| `moonshine-MIT.txt`, `onnxruntime-MIT.txt` | Retained MIT notices |

Measured immutable release record (publication pending clean-machine
verification):

| Field | Value |
| --- | --- |
| Input ID | `moonshine-runtime` |
| Filename | `teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip` |
| Release tag | `moonshine-v0.1.5` |
| Intended immutable URL (not published) | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip` |
| Target | `moonshine/runtime` |
| Size and SHA-256 | 11,455,945 bytes; `718dca3a95fd02eeb02f483fa750500a51a24576dc099c507de48af154c48335` |
| Archive layout | Flat root with the six runtime contract files and `moonshine-MIT.txt`, `onnxruntime-MIT.txt`; no nested directory and no model weights. |
| Upstream revision | `234f60faa0eb388b01cdf7e60aca232af37aefda` |
| License | Component licenses: Moonshine MIT; ONNX Runtime MIT; Microsoft [Visual C++ redistributable terms](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution) for the bundled VC runtime; TeamManager helper code is proprietary under Race Engineer's TeamManager LICENSE. The ZIP has no single umbrella license. |

Build command (Developer PowerShell for VS 2022, Windows x64):

```powershell
./internal/stt/moonshine/native/build-moonshine-helper.ps1 `
  -SdkArchive <moonshine-voice-windows-x86_64.tar.gz> `
  -OutDir <staging>/moonshine/runtime
```

The measured Windows x64 build used Visual Studio Build Tools 17.14.40,
MSVC 19.44.35228.0, Windows SDK 10.0.26100.0, and CMake's Visual Studio 17
2022 generator. It completed with exit code 0. The extracted runtime archive
answered `health`, loaded each of the Tiny, Small, and Medium English model
directories, completed `stream_begin`/audio/update/finish/`stream_close`, and
answered `shutdown`; each helper process exited with code 0. The smoke input
was a synthetic 16-kHz mono PCM16 English phrase, so this record makes no
clean-machine, microphone, or iRacing performance claim.

## Optional model downloads

The three English streaming models are packaged as one ZIP per model. Every
archive contains exactly the eight upstream `quantized_26_08_21` files at the
archive root. The bytes were reproduced from the pinned upstream files and the
packages are published as immutable release assets.

| Input ID | Archive | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `moonshine-tiny-streaming-en` | `moonshine-tiny-streaming-en-quantized_26_08_21-r1.zip` | 36624898 | `41e1882d3ddc7c8a70778224879c929f9b4d87f77c57e9f031757bb27751e3c5` |
| `moonshine-small-streaming-en` | `moonshine-small-streaming-en-quantized_26_08_21-r1.zip` | 121672393 | `ce697ac0dcf1b5b949b4ba1beba4dd19e2c2042c335e26e620ff28706ef8de00` |
| `moonshine-medium-streaming-en` | `moonshine-medium-streaming-en-quantized_26_08_21-r1.zip` | 236904989 | `d22e9adbb0232db4fcc2d5594d0155965efd47222fccd59cda38dd84f0e07305` |

Release tag: `moonshine-v0.1.5`. Target directories:

- `moonshine/optional/moonshine-tiny-streaming-en`
- `moonshine/optional/moonshine-small-streaming-en`
- `moonshine/optional/moonshine-medium-streaming-en`

Every extracted file is verified individually. The measured per-file values
for the pinned catalog:

| File | Tiny bytes | Small bytes | Medium bytes | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `adapter.ort` | 1319664 | 2870368 | 3651296 | Tiny `22ecc949e146c49667fda28d102d4e30749a107dc88a396292aa8f277ef1347c`; Small `c665f742364febad597cc9ac1e0b341ffbee0e24a1466e2f3bde95e6e4771762`; Medium `3f2a287def57cc094367a0eec3c4f5fc36a32ec420e86764b696920991b20281` |
| `cross_kv.ort` | 1287544 | 5356536 | 11643776 | Tiny `143a36667b8d05fd9d04e8c337b7ee121f37ef299aea6b3d82bdb3d3401950b4`; Small `e2d3417144e9514055ebfefe8dcc4c0a55a55adcb8530435844c75c53e352bf6`; Medium `642f6e21cd305be79342207c6f9e6b681d469d55bc48c72b27b84846fb71fd1e` |
| `decoder_kv.ort` | 32583720 | 81878600 | 146972408 | Tiny `8852553f312adb6c9aa4d17418015049b30f412209ee569d336548c0044627de`; Small `1a05465b1dd955858dfcbee039c0020fb5dd982b0f5094c34e61735d518d771b`; Medium `193bb366492b74fc4ad338c6778e8d8eb916aaa11b5aa264f9057f4db7759486` |
| `encoder.ort` | 7675440 | 44148576 | 94705376 | Tiny `a8414e1a5dedf9f2093d7680601dd8a9b0433e7020260eafe0e370ead91134ca`; Small `2d4d973e91e8aca08c51e7e7efa28a46ab265b63d809d5294d18b86bcd85b993`; Medium `12915e76ebac7dd287c5ea63965d06103a53ba1ce242a4a34f318f3958c60c37` |
| `frontend.model.ort` | 23344 | 26944 | 28720 | Tiny `5121b561417b638afce0c6c31b760e37c93cf97f80d9b0031aad1fe7b6f25d61`; Small `09b1210ae30dc5f0f3e45f0ebab914c254741323114f53fbbe5ae62cca35058f`; Medium `95768855c70c8251eeecc05fedf69999da1b8ab16f605c9f457fd3354b0ad6b5` |
| `frontend.weights.ort` | 2093464 | 7769464 | 11889560 | Tiny `217da24ac6f522ebf02da8ef288e77d1ac68d50d4a6821433182e4fbf4204bbd`; Small `7ef97521bd4bad3928f5bb6808586f4fcc6e92bd5990394112eed7d4052ec338`; Medium `5ac941f490cbe035b335b99a414cc393d62d4c6f9f2423495b286870d271d709` |
| `streaming_config.json` | 509 | 512 | 513 | Tiny `74fe5ddebd63b17caf59e8a3b18c17547ff7bce1642050edbb1c3962674f8950`; Small `26f02b6afb22d60871a5efd85c3d38e569cc0ddb6c5eb6e93d3260152ae8a47a`; Medium `28e83b7a28e91472692a035e0dae3116422ae43aeb2bef5ed822c44ce89b88af` |
| `tokenizer.bin` | 249974 | 249974 | 249974 | `6884b35fd6377d4c4d32336a0bc152f36b64d1e45b6503683cdc238250a8472d` |

Extracted totals: Tiny 45,233,659 bytes; Small 142,300,974 bytes; Medium
269,141,623 bytes.

## Reproducing the model archives

```powershell
python scripts/package-moonshine-models.py --out <staging>
```

The script downloads the pinned files from
`https://download.moonshine.ai/model/<model>/quantized_26_08_21/`, verifies
each one against the exact size and SHA-256 above, and writes deterministic
ZIPs (sorted entries, fixed 1980-01-01 timestamps, deflate level 9) plus a
JSON record file. The pinned per-file values are measured from upstream, not
copied from an upstream manifest.

## Approved optional downloads

The closed list of post-install Speech to Text downloads is now:

- `whisper-small-q5_1` (existing)
- `moonshine-tiny-streaming-en`
- `moonshine-small-streaming-en`
- `moonshine-medium-streaming-en`

The list is closed. There is no remote catalog, marketplace, or arbitrary
download path; production clients fetch only pinned TeamManager Forgejo
release assets.

## License material

- The runtime ZIP is a mixed-license component bundle; it is not represented
  as a single MIT-licensed work. The Moonshine SDK/library is covered by the
  Moonshine MIT notice, ONNX Runtime by its MIT notice, and the VC runtime DLLs
  by Microsoft's redistributable terms. The TeamManager helper code remains
  proprietary under Race Engineer's TeamManager LICENSE; these third-party
  notices do not reclassify it.
- Moonshine and the three English streaming models are MIT licensed. See
  `LICENSES/moonshine-MIT.txt` (the v0.1.5 repository license) and the
  upstream model cards.
- ONNX Runtime is MIT licensed. See `LICENSES/onnxruntime-MIT.txt` (retained
  at `core/third-party/onnxruntime/LICENSE.txt` in the v0.1.5 tree).
- The VC runtime DLLs are Microsoft redistributables. They are copied from the
  installed Visual Studio redistributable directory by the helper build
  script; no separate license file is published by that directory.
- The runtime package ships the MIT notices beside the helper binaries. The
  model archives intentionally contain exactly the eight model files and no
  notice files, so the exact-file verifier stays closed; the notices shipped
  with Race Engineer (`LICENSES/` in this repository and in race-engineer-go)
  provide the attribution for the downloaded models.
