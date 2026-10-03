# TeamManager Models

`teammanager-models` is immutable build-input storage for TeamManager's
private Alpha. Forgejo is canonical; GitHub, where present, is only a mirror.

Race Engineer does **not** fetch this repository's `manifest.json`, signature,
checksum sidecars, release metadata, or a catalog at runtime. Required Alpha
components are verified while building Race Engineer and packaged into the one
complete Windows installer. This repository is not a runtime model registry.
Only these explicitly selected optional Speech to Text models may be
downloaded after installation, and only after an explicit user action:

- Whisper `small-q5_1`
- Moonshine `moonshine-tiny-streaming-en`
- Moonshine `moonshine-small-streaming-en`
- Moonshine `moonshine-medium-streaming-en`

The list is closed. A downloaded model is never selected automatically, and
Whisper Base remains the stable default.

Moonshine provenance, the pinned upstream release, and the packaged archive
integrity values are in
[docs/moonshine-alpha31.md](docs/moonshine-alpha31.md).

The exact Alpha inputs, integrity values, licences, and provenance are in
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
