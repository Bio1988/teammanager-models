# TeamManager Models

`teammanager-models` is immutable build-input storage for TeamManager's
private Alpha. Forgejo is canonical; GitHub, where present, is only a mirror.

Race Engineer does **not** fetch this repository's `manifest.json`, signature,
checksum sidecars, release metadata, or a catalog at runtime. Required Alpha
components are verified while building Race Engineer and packaged into the one
complete Windows installer. This repository is not a runtime model registry.
Only the explicitly selected optional Whisper `small-q5_1` model may be
downloaded after installation; it is never downloaded or selected
automatically.

The exact Alpha base inputs, integrity values, licences, and provenance are in
[docs/alpha-build-inputs.md](docs/alpha-build-inputs.md), with the current
stock-voice records in [docs/alpha-voice-contract.md](docs/alpha-voice-contract.md).
Race Engineer records them in its closed `build/alpha-models.lock.json`; that
lock is the build-input contract. The build then generates local
`model-pack.json` inside the installer.
`model-pack.json` is the local runtime descriptor: it contains installed paths,
not network URLs, and is not a model catalog or authority.

The current English stock-voice reconciliation is recorded separately in
[docs/alpha-voice-contract.md](docs/alpha-voice-contract.md). Race Engineer's
runtime selection is Charles, Michael, and Eve, with Charles as its default;
Models records the asset provenance and release eligibility, but does not choose
runtime behavior. The three stock voice files are still immutable upstream
sources, not Forgejo release assets. They therefore block a private/offline
Alpha release until reviewed Forgejo copies and licence material exist.

`manifest.json` is retained solely as historical provenance for already
published Pocket R3 assets. It is not a runtime authority and must not evolve
into another model-manifest generation, catalog, publication protocol, or
signature scheme. Existing immutable release assets and their included licence
and attribution material remain available unchanged.

This repository intentionally has no model publication, signing-candidate,
candidate-evidence, application-update-channel, or runtime-manifest workflow.

The retired signed public application-update-channel design is retained as
[historical documentation](docs/archive/alpha-channel.md). Private Alpha
updates instead use TeamManager Server's authenticated release endpoints to
deliver the next complete installer.
