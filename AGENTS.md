# TeamManager Engineering Rules

## Source of truth

1. Current Forgejo `main` asset records and documentation.
2. The current Forgejo issue or PR.
3. This local `AGENTS.md`.
4. This repository's README and current build-input documentation.
5. Local Current OpenSpecs for relevant contracts.
6. `teammanager-program` for suite direction, ownership, and
   cross-repository priorities.

Forgejo is canonical; GitHub is a mirror. Archived plans, handoffs, old
status snapshots, fixture evidence, and completed OpenSpec changes are not
current authority.

## OpenSpec and documentation

Use OpenSpec only for breaking contracts, authentication/authorization,
simulator-control safety, high-risk migrations, or privacy/retention changes.
Ordinary documentation corrections, asset notes, cleanup, and dependency work
belong in normal issues or PRs.

Do not make a Current claim without a real consumer. Do not keep parallel
roadmaps, exact-SHA status lists, registries, generators, or governance
infrastructure. Archive completed or superseded documentation; research and
handoffs are not product commitments.

## Models boundary

- This repository stores immutable Forgejo release assets, licences,
  attribution, and provenance; it is not a runtime model registry.
- Race Engineer's closed build input lock and installed local model-pack, not
  this repository's historical manifest, determine its Alpha runtime.
- Only the explicitly selected optional Whisper model can be downloaded after
  installation; it is never selected or fetched automatically.
- Do not add remote catalogs, runtime manifests, signing-candidate workflows,
  or application-update-channel machinery.
