# Validation Contract — "English" sprint

> Frozen on 2026-09-26 before the first change. Scope: user request "put everything in English, remove all French from this repo".

## Automated Acceptance Criteria

- [ ] E01: no tracked file contains French accented letters or French quotation marks (guard test).
- [ ] E02: no tracked file name contains a French word (`commun`, `outillage`, `mesure`).
- [ ] E03: script identifiers, docstrings, comments and CLI messages are English; flags `--file`, `--name`, `--exclude`, `--register`, `--dir`, `--status`, `--variant-b` exist; the old French flags are rejected (exit 2).
- [ ] E04: canon is `agents-common.md` with marker `BEGIN:agents-common v2.0`; registry `agents-common.versions.json` keeps v1.0 and v1.1 with unchanged fingerprints and adds v2.0.
- [ ] E05: `version` exits 0.
- [ ] E06: `check .` and `check . --file template/AGENTS.template.md` exit 0.
- [ ] E07: a repo with an intact legacy v1.1 block (`agents-commun` markers) is "behind"; `sync` migrates it to v2.0 with `agents-common` markers and a byte-identical §7.
- [ ] E08: same for an intact legacy v1.0 block.
- [ ] E09: a hand-edited legacy block is refused by `sync` without `--force`.
- [ ] E10: a file mixing a legacy block and a new block is reported as invalid markers.
- [ ] E11: `adopt` writes an English §7 header; `init` writes an English AGENTS.md with `<REPO NAME>` replaced.
- [ ] E12: `init --ledger` creates English ledger templates.
- [ ] E13: `ledger` messages are English and every previous ledger behavior is kept.
- [ ] E14: every previous test is ported (at least 43 tests) and green.
- [ ] E15: the v2.0 block has the same structure as v1.1 (same sections, same number of bullets and steps per section).
- [ ] E16: the v2.0 block is under 8 KB; its token count is measured against v1.1 (o200k and Claude legacy tokenizers).
- [ ] E17: `uvx ruff@0.16.9 check scripts tests`, unittest and `ledger . --strict` are green locally.
- [ ] E18: GitHub CI is green after push.
- [ ] E19: `log.md` is translated entry by entry (same count, dates and types).
- [ ] E20: `docs/journal/` archives are translated and renamed without French words.

## Evaluation Protocol

* `uv run --no-project python -m unittest discover -s tests -v` · `uvx ruff@0.16.9 check scripts tests`
* `uv run --no-project python scripts/sync_agents.py version | check . | ledger . --strict`
* Real path: simulated fleet with legacy v1.0 / v1.1 blocks taken from git history → `audit` → `sync` → `audit --strict`.
