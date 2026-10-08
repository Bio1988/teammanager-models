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
- Every file Race Engineer builds in or offers (including the VCTK voices and
  the intent encoders) is an unmodified upstream or TeamManager-packaged
  Forgejo release asset here; record the immutable source revision, size, hash,
  licence, and attribution. Hugging Face is provenance only.
- Under the current Race Engineer lock (model pack `alpha-5`), the Speech to
  Text downloads after installation are `moonshine-tiny-streaming-en` and
  `moonshine-medium-streaming-en`, solely after explicit user action and never
  automatically. `moonshine-small-streaming-en` is required and packaged in
  the installer. The optional DistilUSE intent encoder is likewise downloaded
  on user action; E5 and MiniLM L12 are pinned but not offered.
- That closed list applies to Speech to Text and intent models. The separately
  authorized managed Radio provider may download only the pinned llama.cpp CPU
  runtime and either the Granite 4.0 350M Q8_0 (default) or the experimental
  Gemma 3 270M IT Q8_0 model package listed in `docs/managed-radio-assets.md`,
  after explicit user action; Gemma needs click-to-accept of its terms. The
  retired Granite 4.0 H and LFM2.5 releases stay published. Keep those packages
  outside the Alpha installer lock. Model selection is also explicit.
  Downloading only installs files and does not activate the provider; selecting
  a model while Engine is running may warm its runtime, while enabling or using
  the provider remains explicit.
- Do not add runtime catalogs, remote default-model manifests, signing-candidate
  workflows, or candidate-evidence protocols.
- Preserve immutable published release assets and their associated integrity and
  provenance records.

## Engineering best practices

These rules apply to all new code and to code a change touches. Existing outliers are not rewritten wholesale; they must not grow, and they are improved when a change touches them.

### All repositories

- Keep new source files under 800 lines (tests under 1200). A file that would cross 1500 lines is split by responsibility in the same change.
- One package or module has one responsibility. Composition roots (`main`, `app` wiring) wire; they do not hold domain logic.
- No alpha numbers, issue numbers, review rounds, OpenSpec ids or dates in identifiers, file names, package names, branch names or test names. Name things by behaviour; traceability belongs in commit messages and PRs.
- Before adding a helper, search this repo, the shared packages and `@teammanager/ui`. Logic that exists in two repos is extracted to a shared module instead of a third copy.
- Generated output (bindings aside, which are checked for drift), build output, test results and reports are not committed.
- Remove dead code in the change that makes it dead. No TODO without a linked issue.
- CI runs the same gates as the documented local commands; a PR states which gates it ran.

### Documentation

- One authoritative document per topic; superseded plans, handoffs and completed OpenSpec changes are archived, not linked from active docs.
- README and AGENTS.md list the authoritative documents; everything else is history.

## Working agreements

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

## Worktrees, branches and test runs

- Work in a dedicated git worktree next to the primary clone (`/home/jarvis/Projects/Team-Manager/<short-name>`), created from current Forgejo `main`.
- When the pull request is merged or abandoned, remove the worktree (`git worktree remove`) and delete the local and remote branch. Do not keep finished worktrees around.
- Run at most one heavy test suite (Playwright, full `npm test`, `go test ./...`) per worktree at a time, and wrap it with `mem-guard 8000000 <command>` (`~/.local/bin/mem-guard`) so a runaway process cannot exhaust the machine.
- In JavaScript tests, never compare DOM nodes with `assert.equal`/`assert.deepEqual`; use identity checks such as `assert.ok(a === b, "…")`. A failing assertion otherwise renders the whole DOM graph and can consume all memory.

## Codex CLI only

This section applies to OpenAI Codex CLI (and OpenCode when explicitly requested). Claude Code does not follow it; its routing lives in `CLAUDE.md`.

### Model routing and delegation

Use the cheapest model that can reliably complete a bounded task. Decompose complex work into small, independently verifiable work packages before implementation. Each package states the goal, relevant scope/files, constraints and non-goals, expected result, and validation/tests. Prefer fresh work packages over switching models inside one long conversation. Parallelize only genuinely independent packages with separate ownership.

- `gpt-6-luna` is the default high-volume worker for discovery, read-only evidence gathering, locating code and tests, documentation, tests, mechanical changes, and small bounded implementations. Use `xhigh` effort. Luna must not redefine architecture or broaden scope; report blockers with evidence.
- `gpt-5.6-luna` is a selective fallback after a failed bounded Luna task, for a second narrow bug hunt, or when a different generation improves debugging. Use `xhigh` effort.
- `gpt-6-sol` handles clearly specified medium-complexity implementation, multi-file changes, and isolated refactors with `high` or `xhigh` effort. `gpt-5.6-sol` handles difficult or high-reliability implementation involving state, concurrency, persistence, migrations, contracts, difficult debugging, or recovery, with `medium`, `high`, or `xhigh` effort.
- Reserve `gpt-6-astra` for architecture, ambiguity, decomposition, difficult failures, and final acceptance. Implementation and acceptance are separate responsibilities. Astra independently inspects the diff and surrounding code; the implementing model selects review effort (`medium`, `high`, or `xhigh`) from actual complexity and risk. Use `medium` for ordinary review, `high` for coupled/API/persistence/lifecycle changes, and `xhigh` for architecture, concurrency, risky migrations, release-critical work, or repeated failure. Review correctness, scope, regressions, complexity, duplication, dead code, architecture, and validation; passing tests alone is insufficient. Meaningful implementation work requiring review is accepted by Astra.

Use the escalation path `gpt-6-luna -> gpt-5.6-luna or gpt-6-sol -> gpt-5.6-sol -> gpt-6-astra`. Escalate for reasoning depth, coupling, risk, ambiguity, or a failed worker, not line count. Workers report changed files, validation, uncertainty, and exact blockers. If Astra finds a problem, send concrete findings to an appropriate worker for repair; after one repair cycle with the same class of failure, escalate instead of repeating it.

OpenCode is an optional worker only when the user explicitly requests it, limited to discovery or cheap bounded work using `opencode-go/deepseek-v4.1-flash` or `opencode-go/glm-5.3-flash`. It is never an automatic fallback, architecture authority, or final reviewer. Do not invoke other agent CLIs or install additional agent CLIs or wrappers without explicit user instruction.

This policy concerns coding agents, not the product's speech or inference models.

Prefer the simplest adequate solution. Reuse existing code and libraries; add frameworks, abstractions, services, interfaces, or parallel architectures only when the current requirement makes them necessary.
