# TeamManager Engineering Rules

## Goal

Ship the smallest safe implementation that solves the current real product need. Prefer working software, simple code, focused tests, and deletion of obsolete code over speculative architecture, governance artifacts, or future foundations.

## Source of truth

1. Current Forgejo `main` source and tests.
2. The current Forgejo issue and PR.
3. This `AGENTS.md`.
4. `README.md` and `docs/architecture.md`.
5. OpenSpec only when explicitly required below.

Old plans, cached SHAs, manifests, completed task lists, fixture hashes, and archived specifications are not current product authority.

## Before changing code

- Fetch and inspect the current Forgejo `main`.
- Read only files relevant to the requested behavior.
- Identify the active runtime consumer before preserving an abstraction.
- Do not read the full documentation tree or create planning/evidence PRs before implementation.

## Simplicity rules

- Prefer the standard library, then an established maintained library.
- Do not create custom parsers, migration runners, queues, crypto protocols, schema validators, retry/rate-limit frameworks, UUID formats, backup systems, event buses, or dependency-injection frameworks.
- Add an interface only for an external boundary, two current implementations, or a useful test seam.
- A normal feature may live in one package; do not require domain/application/infrastructure/interfaces layers.
- Do not add future packages, DTOs, migrations, feature flags, canonical-byte/digest/evidence/witness/epoch/generation/fence/lineage/lease machinery without a current runtime consumer and concrete failure.
- Delete a replaced path in the same wave. Git is rollback.

## OpenSpec

OpenSpec is required only for a breaking external API or wire change, an irreversible/high-risk data migration, authentication/authorization semantics, simulator-control safety semantics, or a retention/privacy policy change.

Bug fixes, internal refactors, ordinary CRUD/UI/query work, dependency updates, tests, and dead-code deletion do not require OpenSpec. When required, proposal, design, tasks, implementation, and tests belong in one PR.

## Security

- Never store passwords, access tokens, refresh tokens, session tokens, or device tokens in plaintext where a database leak exposes them.
- Use established cryptography: authenticated encryption for recoverable provider tokens and a one-way digest for high-entropy session/device tokens.
- Never use SHA-256 as a password hash or log secrets/sensitive payloads.
- Relay stays read-only; simulator commands stay local behind `SafetyGate`.

## Database

- Prefer PostgreSQL constraints and atomic SQL; default to `READ COMMITTED`.
- Use stronger isolation or locks only for a reproduced anomaly not solved by a constraint or atomic statement.
- Start one transaction in the owning use case. Do not build generic transaction/repository/unit-of-work frameworks or evidence tables for ordinary decisions.

## Delivery

- One user-testable vertical slice per PR; no acceptance/evidence/sentinel/documentation prerequisite PR.
- One proportionate review and normal repository checks are enough.
- Infrastructure replacement deletes the old implementation or names its next-wave deletion.
- No production deployment or real secrets without explicit owner authority.

## Complexity budget

Every PR states production files, packages, dependencies, and database tables added/deleted; the old path removed; and why any net architecture increase is necessary.
## Models-specific rules

- This repository stores immutable Forgejo release assets, licences, attribution,
  and provenance; it is not a runtime model registry.
- `manifest.json` is historical provenance only. Do not evolve it or make it a
  runtime authority.
- Race Engineer pins required Alpha inputs in its closed
  `build/alpha-models.lock.json` and packages them into the complete Windows
  installer.
- Only `whisper-small-q5_1` may be downloaded after installation, solely after
  explicit user action and never automatically.
- Do not add runtime catalogs, remote default-model manifests, signing-candidate
  workflows, or candidate-evidence protocols.
- Preserve immutable published release assets and their associated integrity and
  provenance records.

## Codex Model and Execution Policy

Use `gpt-6-astra` for TeamManager orchestration, planning, and independent
review. Use `gpt-5.6-luna` for discovery, implementation, test execution, and
documentation work unless the user explicitly selects another model. Preserve
supported reasoning effort; use `low` instead of `none` or `minimal`, and
`xhigh` for Luna work previously assigned unsupported `ultra` effort. Use the
configured TeamManager roles or explicitly select the matching model for a
generic worker. Do not silently replace Luna workers with Astra, Terra, or Sol.
This policy concerns the coding agent, not the product's speech or inference
models.

### Task Execution & Autonomy
- For implementation or fix requests, carry the authorized work through implementation and relevant verification. Do not stop at a proposed plan when you can proceed.
- Make reasonable assumptions for routine, reversible decisions. Ask a focused question when missing information materially affects correctness, scope, or authorization.
- Continue with authorized read-only actions, local worktrees, branch edits, and appropriate tests without repeatedly asking.
- Before requesting approval, finish the preparation that is already authorized and present a concrete, reviewable result.
- Respect required approval gates. Ask before destructive, irreversible, or otherwise unauthorized actions.
- Avoid boilerplate warnings about hypothetical risks. Explain concrete blockers or material risks when relevant.

### Instruction Conflicts
- Explicit user instructions take precedence over conflicting skill guidelines, subject to higher-priority instructions and actual permission boundaries.
- If a skill causes a pause or deviation, identify the file and relevant rule, and explain whether it is an explicit requirement or your interpretation. Continue any unaffected authorized work.

### Style & Output
- Lead with the result. Use plain language, active voice, and concise paragraphs. Include technical details that help assess the work.
- Use lists when they improve readability; avoid repetitive transitions and stock phrases such as "it's worth noting", "delve", "leverage", and "Bottom line".
- Report what changed, what was verified, and any remaining uncertainty.

### Verification
- Match verification to the scope and impact of the change. Complete required checks; expand testing when a concrete unresolved concern justifies it.

Continue across completed subtasks while the user's authorized objective still
has necessary work. A checklist boundary alone is not a reason to stop. Honor
an explicit planning-only request or requested pause. Do not create separate
user-visible Codex tasks unless the user asks for them. Existing independent
review, merge, release, and production approval requirements still apply;
approval already given in the current task need not be requested again.
