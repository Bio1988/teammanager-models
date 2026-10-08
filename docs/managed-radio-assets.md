# Managed Radio optional assets

The managed Radio answer provider uses one optional Windows CPU runtime and one optional model package. The Race Engineer app catalog offers two pure-transformer models, IBM Granite 4.0 350M Q8_0 (recommended) and Google Gemma 3 270M IT Q8_0 (experimental). Pure transformers let llama.cpp reuse the cached system prompt between requests; the hybrid Granite 4.0 H 350M re-evaluates the prompt each time and is no longer offered by the app. The Granite-H and LiquidAI LFM2.5-350M Q8_0 releases stay published on Forgejo (immutable) for installed apps that still reference them. These assets are not part of the Race Engineer Alpha installer or `build/alpha-models.lock.json`. Each download requires explicit user action, and model selection is a separate explicit action. Downloading only installs files; selecting a model while Engine is running may warm its runtime, while enabling or using the provider remains explicit.

## Package choices and publication state

The Granite 4.0 H model remains the immutable published r1 asset, retired from the app catalog on 2026-10-08 but not deleted while released app versions may reference it. The LFM archive is published and immutable under tag `managed-radio-lfm-2-5-350m-r1`. The r1 runtime also remains immutable, but it omitted the app-local Microsoft Visual C++ runtime files imported by llama.cpp. Its self-contained r2 replacement is published and immutable under tag `managed-radio-granite-350m-r2`. Both model choices use that same b8696-r2 runtime.

| Package ID | State | Asset URL | Archive bytes | Archive SHA-256 |
| --- | --- | --- | ---: | --- |
| `llama-cpp-b8696-win-cpu-x64-r2` | Published immutable | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-granite-350m-r2/runtime-b8696-win-cpu-x64-r2.zip` | 37462006 | `89d990f6aacbe127b5c48b145939f92dc3cbc3779c46b77fe11e844c3d46ab23` |
| `granite-4.0-h-350m-q8-0` | Published immutable | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-granite-350m-r1/granite-4.0-h-350m-q8-0.zip` | 366207248 | `e33d587d6fe6900de41bd965c8551656228a6571d81846d8773dfc48dab16e69` |
| `granite-4.0-350m-q8-0` | Published immutable | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-granite-4-0-350m-r1/granite-4.0-350m-q8-0.zip` | 378149644 | `027a767247495c27857cdd37f7ad3e6025573a7754ddf08e964c35f0be2c4445` |
| `gemma-3-270m-it-q8-0` | Published immutable | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-gemma-3-270m-it-r1/gemma-3-270m-it-q8-0.zip` | 291559385 | `3502edf6e920094088d400506472120744223da2fe94709416649989caadb8ec` |
| `lfm2.5-350m-q8-0` | Published immutable | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-lfm-2-5-350m-r1/LFM2.5-350M-Q8_0.zip` | 379228488 | `b059557558b883274c7bcba58427fe9bc6da6bda451ef59621c70cc75af38390` |

The archives are flat ZIPs with sorted root files, fixed 1980-01-01 timestamps, regular-file mode 0644 and no compression. The existing runtime/Granite build rejects path separators, duplicate names, directories, links, encrypted source entries, and source size/hash mismatches. The LFM ZIP contains exactly the two files listed below. Exact extracted sizes and hashes are recorded below.

### Runtime package files

It contains `llama-server.exe`, all 20 DLLs from the pinned upstream Windows CPU archive, the three Microsoft runtime DLLs required by the PE dependency closure, and the listed source/dependency license texts. Other executables in the source archives are excluded.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `LICENSE-cpp-httplib-MIT.txt` | 1075 | `4b45cbe16d7b71b89ae6127e26e0d90a029198ca5e958ad8e3d0b8bbed364d8b` |
| `LICENSE-libomp-Apache-2.0-with-LLVM-exception.txt` | 15140 | `3340babe8ac7bc6ae294d93aa01c310a250d43d5b760e5c12954882d4e5c83c7` |
| `LICENSE-llama.cpp-MIT.txt` | 1078 | `94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d` |
| `LICENSE-nlohmann-json-MIT.txt` | 1075 | `c0d068392ea65358b798b8c165103560f06e9e3b38c4ab4e2d8810a7b931af86` |
| `NOTICE-Microsoft-Visual-Cpp-Redistributable.txt` | 746 | `c386b552f0b37ea63eb452b8a60a7f711c21fdf48093170250aeda36fb27ecf8` |
| `ggml-base.dll` | 687616 | `62dbab5e20eda426f0091f0b51d9c1e166c6a3bd3e62731cdf439d3eed44377a` |
| `ggml-cpu-alderlake.dll` | 1131008 | `fbcd9da624c45dd7b05e8eb09172dc2a17b0660827087f2de9b385e3382da2c5` |
| `ggml-cpu-cannonlake.dll` | 1369600 | `ff266d639d59884703cd094f2d54e87bff1d7b958b0f828154b84dd64180c65a` |
| `ggml-cpu-cascadelake.dll` | 1355264 | `b08fb5de3ebc28d1aada4b20cff34434541418a85c9e36105771697fd49c1c0d` |
| `ggml-cpu-cooperlake.dll` | 1356288 | `b257cb1af742d47181d1095399200fdc39ada55090635cd3dee81e2f34ad48da` |
| `ggml-cpu-haswell.dll` | 1136128 | `efbd60d78710da9d0e1f13b40749cf4a30805ba8fc474bb2739aabe99dd3ae95` |
| `ggml-cpu-icelake.dll` | 1362944 | `57f34e34cd8b3acfd5bfc629bbc0442d9ab2d6f45bff79809dbc8d8a57f15190` |
| `ggml-cpu-ivybridge.dll` | 1030144 | `ae9c5b61a506afc3143cdc7940ca6eff6146d64d8aa7fff237a147bb2038b3df` |
| `ggml-cpu-piledriver.dll` | 1032704 | `feb56bc5607ddcb056583a1075b9546bfe4d5cdd8bc683cbab05d5d11f2ad444` |
| `ggml-cpu-sandybridge.dll` | 1010176 | `0ac5c226164eea35c03575018ace570fe16c610571b4bca617c2f6958c937a92` |
| `ggml-cpu-sapphirerapids.dll` | 1631232 | `28281af0ff893aaab950b2e9d3939e818f4aad7f7c3825104a7a57aa37409e4f` |
| `ggml-cpu-skylakex.dll` | 1362432 | `06792909e190e8b9744bd9283cd393c582247289d47a35275f4cf3a820237763` |
| `ggml-cpu-sse42.dll` | 850432 | `1819700a3abefac5ab8cb346a61580bb407243a9174eb97c62d3ee60b578a067` |
| `ggml-cpu-x64.dll` | 844288 | `ade0caceced0b86a286259713fdfbc7862bd9abb0b606c1af0cc6c2150c746ec` |
| `ggml-cpu-zen4.dll` | 1363456 | `990b6fdf0f0eb8698f5446fc5834a7cd5043e5f3ec7424522051d6dbd8642f7b` |
| `ggml-rpc.dll` | 143872 | `636fd56252bc0472833e9ecc614591b51d90483d9faeba29669f800adabe60a0` |
| `ggml.dll` | 96768 | `06bc178439f2062b9668ef854f8b6a2c9dbf996c5707a1c801bd8d3e18009404` |
| `libomp140.x86_64.dll` | 634936 | `9ab1cb787e52b2a36133899c01c1db1f876067d1471cd224ead85f40a8152b99` |
| `llama-server.exe` | 14663168 | `bc740f977414046f7f61aa98cc4d50a732a18062b16b0a7e38c19e25cc4db6a8` |
| `llama.dll` | 2621952 | `f4654b84782f5f6eee582e4be4b3c3dc89f400d3337e1ee1ef7f6ae4d68555a5` |
| `mtmd.dll` | 1022976 | `cf60552fc2dc8c19f8e0e6e0358933ef2e252e11125044ef6e26a9ac260ddafb` |
| `msvcp140.dll` | 557728 | `0f885b509a685d2bbfa652fed26b5fb31d88fbdab0a978c641d1c7b8aa460aa9` |
| `vcruntime140.dll` | 124544 | `d5e4d9a3e835fa679450145d6a7d94e36573a509317111904d9b3712c30d9066` |
| `vcruntime140_1.dll` | 49792 | `1f2d41c4aa5db0bc33ebf7b66d72943a817d7ce6cbe880502a9403823633093f` |

### Model package files

| Package | File | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Granite | `LICENSE-Apache-2.0.txt` | 11358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| Granite | `granite-4.0-h-350m-Q8_0.gguf` | 366195616 | `c7d9873640dc303b6773dcc44e72e5bdf533e1c95ca8421e6191fbff5c94c942` |
| Granite 4.0 350M | `LICENSE-Apache-2.0.txt` | 11358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| Granite 4.0 350M | `granite-4.0-350m-Q8_0.gguf` | 378138016 | `9595dafb4ed15aa02512c8ea26188744192a6f09530eae0a2747bd3ada96cd36` |
| Gemma 3 270M IT | `LICENSE-Gemma-Prohibited-Use-Policy.txt` | 3980 | `8c7fe01e23c908faee947bc572f6a41abe483feb4012d94c61d5cbd455bc1942` |
| Gemma 3 270M IT | `LICENSE-Gemma-Terms-of-Use.txt` | 9182 | `a155573b609607eb714157ad2fd0f719cc31e7f3fc1673f5eccc5dcf43ceacff` |
| Gemma 3 270M IT | `NOTICE` | 97 | `66f856d7da72797f528fca46b7c80634ab481f917bfe020960e123d84b19f75f` |
| Gemma 3 270M IT | `gemma-3-270m-it-Q8_0.gguf` | 291545600 | `0ef57d2c838458a1952664260dcba38e5bdda37494f3af732f06e4add24068e3` |
| LFM | `LICENSE-LFM-Open-License-v1.0.txt` | 10574 | `4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c` |
| LFM | `LFM2.5-350M-Q8_0.gguf` | 379217632 | `be036a757295e550098b85e13f6af2735d0fa73b41e1156a40c7d8e8e32a5766` |

## Source and license provenance

**Runtime.** The primary source is the official llama.cpp `b8696` Windows CPU x64 release asset (`https://github.com/ggml-org/llama.cpp/releases/download/b8696/llama-b8696-bin-win-cpu-x64.zip`), pinned to source commit `69c28f1547c169902f62ca48bee75fb876c4d8e6`. Its source ZIP is 39345159 bytes with SHA-256 `8e0e2a0d86b5d3f4795a89edb60dc82f70a430dac69897f12e81f2f0cd5260d4`. The curated archive retains `llama-server.exe` and all DLLs, including `libomp140.x86_64.dll`. The included texts cover llama.cpp (MIT), cpp-httplib (MIT), nlohmann/json (MIT), and LLVM OpenMP (Apache-2.0 with LLVM exception). The llama.cpp and vendored license copies come from the pinned source commit; the LLVM license text is the retained upstream LLVM license in `LICENSES/`.

The Microsoft runtime source is the already published immutable Moonshine runtime archive [`teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip`](https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip), tag `moonshine-v0.1.5`, Moonshine source revision `234f60faa0eb388b01cdf7e60aca232af37aefda`, 11455945 bytes, SHA-256 `718dca3a95fd02eeb02f483fa750500a51a24576dc099c507de48af154c48335`. It records Visual Studio Build Tools 17.14.40 as the source environment; the selected Microsoft DLLs report file version `14.44.35211.0`. Static PE inspection found the llama.cpp closure imports `MSVCP140.dll`, `VCRUNTIME140.dll`, and `VCRUNTIME140_1.dll`; every imported symbol is exported by these pinned files. `msvcp140_1.dll` is present in the source archive but is not imported by this closure, so r2 excludes it. The bundled notice links Microsoft’s [Visual Studio license terms](https://visualstudio.microsoft.com/license-terms/) and [Visual C++ redistribution documentation](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution). Actual Windows loading is verified by the product smoke test, not by this static inspection.

**Model.** The source is IBM’s [`ibm-granite/granite-4.0-h-350m-GGUF` repository at revision `a864f823cce6e6048b5752e2816fe7a23987d790`](https://huggingface.co/ibm-granite/granite-4.0-h-350m-GGUF/tree/a864f823cce6e6048b5752e2816fe7a23987d790) file [`granite-4.0-h-350m-Q8_0.gguf`](https://huggingface.co/ibm-granite/granite-4.0-h-350m-GGUF/resolve/a864f823cce6e6048b5752e2816fe7a23987d790/granite-4.0-h-350m-Q8_0.gguf), 366195616 bytes, SHA-256 `c7d9873640dc303b6773dcc44e72e5bdf533e1c95ca8421e6191fbff5c94c942`. Its source repository identifies `ibm-granite/granite-4.0-h-350m` as the base model and marks the package Apache-2.0. The model archive includes the complete Apache-2.0 license text (SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`). The pinned GGUF repository README says it contains GGUF conversions of the IBM base model, but does not record a converter version, conversion command, or base-model revision; this package record does not claim those missing details.

**Granite 4.0 350M (non-H) model.** The source is IBM's [`ibm-granite/granite-4.0-350m-GGUF` repository at revision `b8208a86a58427e1739265318028eb5895b74bf2`](https://huggingface.co/ibm-granite/granite-4.0-350m-GGUF/tree/b8208a86a58427e1739265318028eb5895b74bf2) file [`granite-4.0-350m-Q8_0.gguf`](https://huggingface.co/ibm-granite/granite-4.0-350m-GGUF/resolve/b8208a86a58427e1739265318028eb5895b74bf2/granite-4.0-350m-Q8_0.gguf), 378138016 bytes, SHA-256 `9595dafb4ed15aa02512c8ea26188744192a6f09530eae0a2747bd3ada96cd36` (equal to the Hugging Face LFS object id). The architecture is `granite` (pure transformer) with 352379904 parameters as reported by llama.cpp b8696. The source repository README marks it Apache-2.0 with base model `ibm-granite/granite-4.0-350m`; the archive includes the complete Apache-2.0 text. Like the H variant, the README gives no converter version or command, and none is claimed. Release tag `managed-radio-granite-4-0-350m-r1` also carries `provenance.json` and `SHA256SUMS`.

**Gemma 3 270M IT model (experimental).** Google publishes no Q8_0 GGUF itself, so the source is the llama.cpp organisation's conversion [`ggml-org/gemma-3-270m-it-GGUF` at revision `e7647be17ae1108f2f605ed061ca0608b171afff`](https://huggingface.co/ggml-org/gemma-3-270m-it-GGUF/tree/e7647be17ae1108f2f605ed061ca0608b171afff) file [`gemma-3-270m-it-Q8_0.gguf`](https://huggingface.co/ggml-org/gemma-3-270m-it-GGUF/resolve/e7647be17ae1108f2f605ed061ca0608b171afff/gemma-3-270m-it-Q8_0.gguf), 291545600 bytes, SHA-256 `0ef57d2c838458a1952664260dcba38e5bdda37494f3af732f06e4add24068e3` (equal to the Hugging Face LFS object id); base model `google/gemma-3-270m-it`. The architecture is `gemma3` with 268098176 parameters. The Hugging Face repository carries no license metadata, so the governing text is the [Gemma Terms of Use](https://ai.google.dev/gemma/terms) (last modified 2026-04-01) and the [Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy) (last modified 2024-02-21), captured as text from those pages and stored in `LICENSES/Gemma-Terms-of-Use-2026-04-01.txt` and `LICENSES/Gemma-Prohibited-Use-Policy-2024-02-21.txt`. Release tag `managed-radio-gemma-3-270m-it-r1`.

Gemma redistribution obligations (Terms section 3.1), which the archive and the app must keep satisfying: (1) every recipient gets a copy of the Terms (included as `LICENSE-Gemma-Terms-of-Use.txt`); (2) a `NOTICE` text file with the exact sentence "Gemma is provided under and subject to the Gemma Terms of Use found at ai.google.dev/gemma/terms" accompanies every distribution other than a hosted service (included as `NOTICE`); (3) the use restrictions of section 3.2 (Prohibited Use Policy, applicable law) must be an enforceable provision in any agreement governing use or distribution and recipients must be told that the model is subject to them (the app shows both links beside the model and the archive carries the policy text); (4) modified files must carry prominent modification notices. The GGUF is a Quantized/converted Model Derivative made by ggml-org, not modified by TeamManager; the bytes are redistributed unchanged. Google claims no rights in outputs (section 3.3). Gemma is therefore a restricted-use license, not Apache-2.0, and the app marks it experimental and optional.

**LFM model.** The source is LiquidAI’s [`LiquidAI/LFM2.5-350M-GGUF` repository at revision `657e078c94084481950a2d555a941481f715536b`](https://huggingface.co/LiquidAI/LFM2.5-350M-GGUF/tree/657e078c94084481950a2d555a941481f715536b), file [`LFM2.5-350M-Q8_0.gguf`](https://huggingface.co/LiquidAI/LFM2.5-350M-GGUF/resolve/657e078c94084481950a2d555a941481f715536b/LFM2.5-350M-Q8_0.gguf), 379217632 bytes, SHA-256 `be036a757295e550098b85e13f6af2735d0fa73b41e1156a40c7d8e8e32a5766`. The model has 354483968 parameters. Its license is **LFM Open License v1.0**, copied from [`LiquidAI/LFM2.5-350M` at revision `9e6c6ccf47cd318696e137d381a7ded8fe4df09f`](https://huggingface.co/LiquidAI/LFM2.5-350M/blob/9e6c6ccf47cd318696e137d381a7ded8fe4df09f/LICENSE); the archive includes that complete license as `LICENSE-LFM-Open-License-v1.0.txt` (10574 bytes, SHA-256 `4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c`). The published LFM ZIP is a flat archive with sorted root files, stored entries, fixed 1980-01-01 timestamps, and regular-file mode 0644. The release also includes [`provenance.json`](https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-lfm-2-5-350m-r1/provenance.json) as a separate asset; it records the source pins, file hashes, archive hash, and release URL. This published provenance file preserves the pre-publication field names `proposed_release_tag` and `proposed_release_url`. Those names describe the staging record and do not indicate the current publication state. The sidecar is not a member of the model ZIP.

## Rebuild

The two pure-transformer packages are rebuilt with `scripts/package_managed_radio_transformers.py` (same deterministic ZIP helper). Download both GGUFs from the pinned URLs above into a fresh empty directory, then run `python3 scripts/package_managed_radio_transformers.py --sources <dir> --out <out>`; it verifies sizes and SHA-256 hashes, builds the flat stored ZIPs and writes `provenance.json` (`SHA256SUMS` is `sha256sum *.zip provenance.json`). The archive hashes must equal the table above.

Place the three verified runtime and Granite source files in `artifacts/generative-radio/` and run this from the repository root:

```sh
python3 scripts/package_managed_radio_assets.py \
  --sources ../artifacts/generative-radio \
  --out ../artifacts/managed-radio-assets
```

The command-line build is limited to the r2 runtime and Granite model. It writes their ZIPs and `provenance.json` outside the Git repository, verifies the pinned source archives and selected members, and creates flat deterministic archives. Its JSON records the application package shape: `ID`, `ArchiveURL`, `ArchiveSizeBytes`, `ArchiveSHA256`, and `Files` (`Name`, `SizeBytes`, `SHA256`). The generated runtime `runtime_state` still says `prepared-not-published`, reflecting the packager's pre-publication record; it is build provenance, not the current release state shown above. The script does not publish tags or releases. The repository test suite exercises deterministic output, closed inventories, omission of extra executables, and rejection of unsafe source paths.

The LFM archive uses the same existing `verify_source` and `deterministic_zip` helpers; the command-line build does not include it. Place the model and license from the pinned sources below at `../artifacts/generative-radio/lfm/LFM2.5-350M-Q8_0.gguf` and `../artifacts/generative-radio/lfm/LICENSE-LFM-Open-License-v1.0.txt`. Then run this from the repository root to recreate the flat, uncompressed archive and verify its exact output hash:

```sh
python3 - <<'PY'
from pathlib import Path
from scripts.package_managed_radio_assets import deterministic_zip, verify_source

source_dir = Path("../artifacts/generative-radio/lfm")
model = verify_source(
    source_dir / "LFM2.5-350M-Q8_0.gguf",
    379217632,
    "be036a757295e550098b85e13f6af2735d0fa73b41e1156a40c7d8e8e32a5766",
)
license_text = verify_source(
    source_dir / "LICENSE-LFM-Open-License-v1.0.txt",
    10574,
    "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c",
)
record = deterministic_zip(
    Path("../artifacts/managed-radio-assets/LFM2.5-350M-Q8_0.zip"),
    {
        "LFM2.5-350M-Q8_0.gguf": model,
        "LICENSE-LFM-Open-License-v1.0.txt": license_text,
    },
)
assert (record["archive_size_bytes"], record["archive_sha256"]) == (
    379228488,
    "b059557558b883274c7bcba58427fe9bc6da6bda451ef59621c70cc75af38390",
)
print(record)
PY
```

The source files are the model and license pinned in the provenance section above. The resulting ZIP matches the published immutable asset in the table. The separate provenance asset published alongside it preserves the staging-time keys `proposed_release_tag` and `proposed_release_url`; those names do not change the current release state.

Upstream source pins:

- Granite 4.0 350M: [ibm-granite/granite-4.0-350m-GGUF at `b8208a86a58427e1739265318028eb5895b74bf2`](https://huggingface.co/ibm-granite/granite-4.0-350m-GGUF/resolve/b8208a86a58427e1739265318028eb5895b74bf2/granite-4.0-350m-Q8_0.gguf).
- Gemma 3 270M IT: [ggml-org/gemma-3-270m-it-GGUF at `e7647be17ae1108f2f605ed061ca0608b171afff`](https://huggingface.co/ggml-org/gemma-3-270m-it-GGUF/resolve/e7647be17ae1108f2f605ed061ca0608b171afff/gemma-3-270m-it-Q8_0.gguf).
- Runtime release: [b8696](https://github.com/ggml-org/llama.cpp/releases/download/b8696/llama-b8696-bin-win-cpu-x64.zip); commit `69c28f1547c169902f62ca48bee75fb876c4d8e6`.
- Microsoft runtime files: [published Moonshine runtime](https://forgejo.g-grp.com/Max/teammanager-models/releases/download/moonshine-v0.1.5/teammanager-moonshine-runtime-win-x64-v0.1.5-r1.zip); source revision `234f60faa0eb388b01cdf7e60aca232af37aefda`.
- Model file: [ibm-granite/granite-4.0-h-350m-GGUF at `a864f823cce6e6048b5752e2816fe7a23987d790`](https://huggingface.co/ibm-granite/granite-4.0-h-350m-GGUF/resolve/a864f823cce6e6048b5752e2816fe7a23987d790/granite-4.0-h-350m-Q8_0.gguf).
- LFM model file: [LiquidAI/LFM2.5-350M-GGUF at `657e078c94084481950a2d555a941481f715536b`](https://huggingface.co/LiquidAI/LFM2.5-350M-GGUF/resolve/657e078c94084481950a2d555a941481f715536b/LFM2.5-350M-Q8_0.gguf).
- LFM license: [LiquidAI/LFM2.5-350M at `9e6c6ccf47cd318696e137d381a7ded8fe4df09f`](https://huggingface.co/LiquidAI/LFM2.5-350M/blob/9e6c6ccf47cd318696e137d381a7ded8fe4df09f/LICENSE).
