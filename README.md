# TeamManager Models

`teammanager-models` is immutable build-input storage for TeamManager's
private Alpha. Forgejo is canonical; GitHub, where present, is only a mirror.

Race Engineer does **not** fetch this repository's `manifest.json`, signature,
checksum sidecars, release metadata, or a catalog at runtime. Required Alpha
components are verified while building Race Engineer and packaged into the one
complete Windows installer. This repository is not a runtime model registry.
The current lock (model pack `alpha-5`) makes `moonshine-small-streaming-en` a required
installer input.
For Speech to Text, only these optional models may be downloaded after
installation, and only after an explicit user action:

- Moonshine `moonshine-tiny-streaming-en`
- Moonshine `moonshine-medium-streaming-en`

No Whisper model is in the current lock.
A downloaded model is never selected automatically. The installer also ships
the required all-MiniLM-L6-v2 intent encoder; the optional DistilUSE intent
encoder is downloaded from Advanced on user action. Multilingual E5 Small and
all-MiniLM-L12-v2 are pinned under `optional` but not offered by the app. The
required/optional split and exact asset pins are in
[docs/alpha-build-inputs.md](docs/alpha-build-inputs.md). The three required
VCTK voice files and all intent models are unmodified upstream bytes mirrored
here as Forgejo release assets; no build or runtime input comes from Hugging
Face.

The separately authorized managed Radio answer provider uses one optional
Windows CPU runtime with either IBM Granite 4.0 350M Q8_0 (default) or Google
Gemma 3 270M IT Q8_0 (experimental; the app requires click-to-accept of the
Gemma terms). The retired Granite 4.0 H 350M and LiquidAI LFM2.5-350M releases
stay published for older apps. The runtime and model packages stay outside the
Alpha installer. Downloads require explicit user action; model selection is
separate and explicit. Downloading only installs files; selecting a model while
Engine is running may warm its runtime, while enabling or using the provider
remains explicit. Their closed file inventories, licenses, source pins, and
packaging records are in [docs/managed-radio-assets.md](docs/managed-radio-assets.md).

The exact inputs, integrity values, licences, and provenance are in
[docs/alpha-build-inputs.md](docs/alpha-build-inputs.md). Race Engineer records
them in its closed `build/alpha-models.lock.json`; that lock is the build-input
contract. The build then generates local `model-pack.json` inside the installer.
`model-pack.json` is the local runtime descriptor: it contains installed paths,
not network URLs, and is not a model catalog or authority.

`manifest.json` is retained solely as historical provenance for already
published Pocket R3 assets. It is not a runtime authority and must not evolve
into another model-manifest generation, catalog, publication protocol, or
signature scheme. Existing immutable release assets and their included licence
and attribution material remain available unchanged.

This repository intentionally has no model publication, signing-candidate,
candidate-evidence, application-update-channel, or runtime-manifest workflow.

Run the offline archive reproduction test used by CI with:

```sh
python3 -B -m unittest discover -s scripts -p 'test_*.py'
```

The retired signed public application-update-channel design is retained as
[historical documentation](docs/archive/alpha-channel.md). Private Alpha
updates instead use TeamManager Server's authenticated release endpoints to
deliver the next complete installer.
