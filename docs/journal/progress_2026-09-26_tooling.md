# Sprint Progress

> Translated from French on 2026-09-26 (English sprint); file names, CLI flags, test names and state labels use their current v2.0 names.

## Current Goal
- [x] v1.1 "tooling" sprint: make `sync_agents.py` reliable (no silent loss) and add adopt / ledger / exclusions / version registry, under tests + CI.

## Iteration Milestones
- [x] F-01 Robust reading
- [x] F-02 Fingerprint registry + fine-grained analysis
- [x] F-03 Safe sync + diff
- [x] F-04 audit: exclusions, mixed generated blocks, --strict
- [x] F-05 adopt
- [x] F-06 ledger
- [x] F-07 Tests + CI
- [x] F-08 Documentation

## Contract Validation (2026-09-26)
- C01-C25: covered by `tests/test_sync_agents.py` (41 tests, exit 0) and replayed through the CLI on a simulated fleet (audit, sync, adopt, ledger).
- C26: `unittest` green, `uvx ruff check scripts tests` green, `py_compile` green.
- C27: run #1 (951f819) — tests green, lint red (unpinned ruff: 0.16.9 in CI). Fix 5eba842 (pinned ruff + 5 findings):
  run #2 **fully green** (lint + tests Ubuntu/Windows × 3.11/3.13).
