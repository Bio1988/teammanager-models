# Managed Radio optional assets

These are the two separately installed CPU packages for the explicitly selected managed Radio answer provider. They are not part of the Race Engineer Alpha installer or `build/alpha-models.lock.json`. Downloading either package requires an explicit user action; neither package is selected or started by downloading it.

## Candidate release

The candidate Forgejo release tag is `managed-radio-granite-350m-r1`. Its state is `prepared-not-published`: the tag and release do not exist yet, and no package has been published. The URLs below are reserved candidates; add the assets to that release before using them in the application catalog.

| Package ID | Candidate asset URL | Archive bytes | Archive SHA-256 |
| --- | --- | ---: | --- |
| `llama-cpp-b8696-win-cpu-x64` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-granite-350m-r1/runtime-b8696-win-cpu-x64.zip` | 36728706 | `618d59d17dae0fb74b4dfaae348f0d239a6013a251e3e235a975823b243ba1bd` |
| `granite-4.0-h-350m-q8-0` | `https://forgejo.g-grp.com/Max/teammanager-models/releases/download/managed-radio-granite-350m-r1/granite-4.0-h-350m-q8-0.zip` | 366207248 | `e33d587d6fe6900de41bd965c8551656228a6571d81846d8773dfc48dab16e69` |

Each archive is a flat ZIP with sorted root files, fixed 1980-01-01 timestamps, regular-file mode 0644 and no compression. The build rejects path separators, duplicate names, directories, links, encrypted source entries, and source size/hash mismatches. Exact extracted sizes and hashes are listed below.

### Runtime package files

It contains `llama-server.exe`, all 20 DLLs from the pinned upstream Windows CPU archive, and the listed source/dependency license texts. Other executables in the upstream archive are excluded.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `LICENSE-cpp-httplib-MIT.txt` | 1075 | `4b45cbe16d7b71b89ae6127e26e0d90a029198ca5e958ad8e3d0b8bbed364d8b` |
| `LICENSE-libomp-Apache-2.0-with-LLVM-exception.txt` | 15140 | `3340babe8ac7bc6ae294d93aa01c310a250d43d5b760e5c12954882d4e5c83c7` |
| `LICENSE-llama.cpp-MIT.txt` | 1078 | `94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d` |
| `LICENSE-nlohmann-json-MIT.txt` | 1075 | `c0d068392ea65358b798b8c165103560f06e9e3b38c4ab4e2d8810a7b931af86` |
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

### Model package files

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `LICENSE-Apache-2.0.txt` | 11358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| `granite-4.0-h-350m-Q8_0.gguf` | 366195616 | `c7d9873640dc303b6773dcc44e72e5bdf533e1c95ca8421e6191fbff5c94c942` |

## Source and license provenance

**Runtime.** The source is the official llama.cpp `b8696` Windows CPU x64 release asset (`https://github.com/ggml-org/llama.cpp/releases/download/b8696/llama-b8696-bin-win-cpu-x64.zip`), pinned to source commit `69c28f1547c169902f62ca48bee75fb876c4d8e6`. Its source ZIP is 39345159 bytes with SHA-256 `8e0e2a0d86b5d3f4795a89edb60dc82f70a430dac69897f12e81f2f0cd5260d4`. The curated archive retains `llama-server.exe` and all DLLs, including `libomp140.x86_64.dll`. The included texts cover llama.cpp (MIT), cpp-httplib (MIT), nlohmann/json (MIT), and LLVM OpenMP (Apache-2.0 with LLVM exception). The llama.cpp and vendored license copies come from the pinned source commit; the LLVM license text is the retained upstream LLVM license in `LICENSES/`.

**Model.** The source is IBM’s [`ibm-granite/granite-4.0-h-350m-GGUF` repository at revision `a864f823cce6e6048b5752e2816fe7a23987d790`](https://huggingface.co/ibm-granite/granite-4.0-h-350m-GGUF/tree/a864f823cce6e6048b5752e2816fe7a23987d790) file [`granite-4.0-h-350m-Q8_0.gguf`](https://huggingface.co/ibm-granite/granite-4.0-h-350m-GGUF/resolve/a864f823cce6e6048b5752e2816fe7a23987d790/granite-4.0-h-350m-Q8_0.gguf), 366195616 bytes, SHA-256 `c7d9873640dc303b6773dcc44e72e5bdf533e1c95ca8421e6191fbff5c94c942`. Its source repository identifies `ibm-granite/granite-4.0-h-350m` as the base model and marks the package Apache-2.0. The model archive includes the complete Apache-2.0 license text (SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`). The pinned GGUF repository README says it contains GGUF conversions of the IBM base model, but does not record a converter version, conversion command, or base-model revision; this package record does not claim those missing details.

## Rebuild

Place the two verified source files in `artifacts/generative-radio/` and run:

```sh
python3 scripts/package_managed_radio_assets.py \
  --sources ../artifacts/generative-radio \
  --out ../artifacts/managed-radio-assets
```

The script writes both candidate ZIPs and `provenance.json` outside the Git repository. It verifies the pinned source archives, verifies the Apache and runtime license text, creates flat deterministic archives, and records each extracted file’s exact size and SHA-256. The output JSON uses the application package shape: `ID`, `ArchiveURL`, `ArchiveSizeBytes`, `ArchiveSHA256`, and `Files` (`Name`, `SizeBytes`, `SHA256`). The repository test suite exercises deterministic output, closed inventories, omission of extra executables, and rejection of unsafe source paths.

Upstream source pins:

- Runtime release: [b8696](https://github.com/ggml-org/llama.cpp/releases/download/b8696/llama-b8696-bin-win-cpu-x64.zip); commit `69c28f1547c169902f62ca48bee75fb876c4d8e6`.
- Model file: [ibm-granite/granite-4.0-h-350m-GGUF at `a864f823cce6e6048b5752e2816fe7a23987d790`](https://huggingface.co/ibm-granite/granite-4.0-h-350m-GGUF/resolve/a864f823cce6e6048b5752e2816fe7a23987d790/granite-4.0-h-350m-Q8_0.gguf).
