# Validation Contract — "skills management" sprint

> Frozen before the first line of code (2026-09-28). Scope change = new contract approved by the user.

## Automated Acceptance Criteria

- [ ] C01: `skills add <github-url> --skill <name>` imports the skill folder (SKILL.md + sibling files) into kit `skills/<name>/` (network seam mocked in tests).
- [ ] C02: `add` records in `skills.json`: source `owner/repo`, resolved commit sha, import date, and per-file sha256 fingerprints.
- [ ] C03: `add` refuses an existing skill name without `--force`; with `--force` it replaces the files and refreshes the registry entry.
- [ ] C04: `add --ref <branch|tag|sha>` pins the upstream ref; without `--ref` the default branch HEAD sha is recorded.
- [ ] C05: a kit skill copy that no longer matches `skills.json` (hand-edited) refuses `add --force` without `--force` (no silent overwrite).
- [ ] C06: `skills list` prints every vendored skill with name, source, ref and file count.
- [ ] C07: `skills sync <repo>` installs missing skills into `<repo>/.agents/skills/<name>/` and writes the lock `<repo>/.agents/skills/.agents-kit.json` (per-file fingerprints, source, ref).
- [ ] C08: `sync` on an up-to-date repo writes nothing (mtimes unchanged) and exits 0.
- [ ] C09: `sync` on a behind repo (installed files match the lock, lock older than the kit) updates the files and the lock, exits 0.
- [ ] C10: `sync` on a hand-edited repo (installed file differs from the lock fingerprint) refuses, exits 1, writes nothing for that skill; `--force` overwrites it.
- [ ] C11: `sync --dry-run` prints the planned actions (install/update/prune) and writes nothing.
- [ ] C12: `sync --skill <name>` deploys only that skill.
- [ ] C13: `skills check <repo>` exits 0 up to date, 1 on drift (behind/hand-edited/missing skill), 2 when the repo has no managed skills directory.
- [ ] C14: `skills audit [root]` sweeps every `<root>/<repo>/.agents/skills`; `--strict` exits 1 unless every repo is up to date/none; `--exclude` and `<root>/.agents-kit-ignore` are honored.
- [ ] C15: orphan skills (in the repo lock but no longer vendored in the kit) are pruned by `sync` (listed, removed) and shown by `--dry-run`.
- [ ] C16: a non-UTF-8 or unreadable file produces a clear message, never a traceback (both scripts).
- [ ] C17: no network in unit tests: the GitHub fetch seam is mocked; all import/deploy/compare logic is tested offline.
- [ ] C18: zero dependency: the new script passes a stdlib-only import check; `sync_agents.py` is left untouched (fleet CI keeps the exact same command line).
- [ ] C19: `uvx ruff@0.16.9 check scripts tests` green; the 50 existing tests stay green.
- [ ] C20: the repository stays English-only (the existing English guard tests pass unchanged).
- [ ] C21: docs updated: README section, CHANGELOG entry, kit AGENTS.md §7 (commands + invariants); the common block is NOT modified (no canon version bump).
- [ ] C22: the first real skill (`using-superpowers` from `obra/superpowers`) is vendored through the real `skills add` path, its license identified and recorded, and a real `skills sync` into a simulated consumer repo exits 0 with `check` green.

## Evaluation Protocol

* Test command: `uv run --no-project python -m unittest discover -s tests`
* Lint: `uvx ruff@0.16.9 check scripts tests`
* End to end: real `skills add` (network) then `skills sync` on a temp copy of a consumer repo.
* Expected behavior: all criteria backed by executed commands (exit codes) or file contents, recorded in progress.md.
