@AGENTS.md

# Claude Code

All sections of `AGENTS.md` apply to Claude Code except **Codex CLI only**.

## Model routing and delegation

- The main session orchestrates: it decomposes work into small, independently verifiable packages, chooses the model per package, and accepts or rejects the result after reading the diff.
- Use Sonnet subagents (`model: sonnet`) for discovery, bounded implementation, tests and documentation. Use Haiku only for trivial lookups. Give every subagent a self-contained prompt: goal, files in scope, constraints and non-goals, validation, report format.
- Parallelize only packages with separate files and separate worktrees. Never run two heavy test suites in the same worktree at the same time.
- Review each pull request once, when it is ready to merge (not per push): `claude -p --model claude-opus-5-5 --effort medium` with read-only tools on `git diff forgejo/main...HEAD`. Fix confirmed findings, then merge only when CI is green and the product owner has authorized the merge.

## Forgejo

- Use `tea` (`~/.local/bin/tea`, login `forgejo`) for pull requests, merges, CI runs and workflow dispatch. `gh` only reaches the GitHub mirror.
