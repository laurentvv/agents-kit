# Sprint Progress

## Current Goal
- [x] "English" sprint: the whole repository in English, canon v2.0, fleet migration through `sync` without loss.

## Iteration Milestones
- [x] F-12 Script and tests in English
- [x] F-13 Canon v2.0 in English
- [x] F-14 Docs and ledger history in English
- [x] F-15 English regression guard and token re-measurement

## Contract Validation (2026-09-26)
- E01-E02: `EnglishOnly` tests green (no French character, word or file name); each guard proven by a planted probe (3 probes → red, removed → green).
- E03: flags `--file`, `--name`, `--exclude`, `--register`, `--dir`, `--status`, `--variant-b`; `Cli` test: the former French flags exit 2.
- E04-E05: `agents-common.md` = `BEGIN:agents-common v2.0`; registry v1.0 = 7b36d6d3…, v1.1 = 7b633d73… (unchanged), v2.0 = 3f2aae8d…; `version` exit 0.
- E06: `check .` and `check . --file template/AGENTS.template.md` → UP TO DATE (v2.0).
- E07-E08: real files from git (fc6ebd2 v1.0, 661d531 v1.1): "behind" → `sync` → v2.0 with `agents-common` markers, §7 identical (`cmp`); same for the kit's own AGENTS.md.
- E09: edited v1.1 block → REFUSED (exit 1), file unchanged. E10: `Legacy` test (legacy + new block → invalid markers).
- E11-E12: `init --ledger` → "# AGENTS.md — Fresh Repo", "# Validation Contract"; `adopt` writes "## §7 Project-specific".
- E13-E14: 50 tests green (the 43 previous ones ported + Legacy ×3, Cli, EnglishOnly ×3).
- E15: same sections, bullets, steps, table rows and code fences as v1.1 (script comparison, fences ignored for headings).
- E16: block 6 779 bytes; tokens v1.1 → v2.0: o200k 1 941 → 1 623 (−16 %), Claude legacy 2 369 → 1 746 (−26 %).
- E17: `uvx ruff@0.16.9`, unittest, `ledger . --strict` green locally. E18: GitHub CI to check after push.
- E19: `log.md` translated entry by entry (26 → 26, same dates and types) + one `sync` entry recording it.
- E20: `docs/journal/` translated; `outillage` files renamed `tooling`.
- Caught along the way: the CI still called the old French name of the `--file` flag (would have failed); accent-free French in CI step names (new word guard); a size figure I had not measured yet (corrected to the measured 6 779 bytes).
