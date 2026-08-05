# TeamManager Models

`teammanager-models` is immutable build-input storage for TeamManager's
private Alpha. Forgejo is canonical; GitHub, where present, is only a mirror.

## Suite authority

Suite-wide product direction, repository ownership, and the cross-repository
roadmap are maintained in
[teammanager-program](https://forgejo.g-grp.com/Max/teammanager-program).
The asset and build-input truth remain this repository's Forgejo `main`,
immutable release assets, and current local build-input documentation. OpenSpec
is reserved for breaking contracts, authentication/authorization,
simulator-control safety, high-risk migrations, and privacy/retention changes.

Race Engineer does **not** fetch this repository's `manifest.json`, signature,
checksum sidecars, release metadata, or a catalog at runtime. Required Alpha
components are verified while building Race Engineer and packaged into the one
complete Windows installer. This repository is not a runtime model registry.
Only the explicitly selected optional Whisper `small-q5_1` model may be
downloaded after installation; it is never downloaded or selected
automatically.

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

The retired signed public application-update-channel design is retained as
[historical documentation](docs/archive/alpha-channel.md). Private Alpha
updates instead use TeamManager Server's authenticated release endpoints to
deliver the next complete installer.
