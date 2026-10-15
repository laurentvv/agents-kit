# Validation Contract — "duckdb state ledger" sprint

> Frozen on 2026-10-16 before the first change. Scope: replace the 4-file markdown/JSON ledger
> with a single per-project DuckDB database (`.agent/state.duckdb`) managed by a CLI shipped as
> the `agent-state` skill; transactional migration of legacy ledgers; canon v3.0; fleet rollout
> runbook. The real migrations (kit ledger, fleet repositories) run only on the user's explicit GO.

## Automated Acceptance Criteria

- [ ] D01: `scripts/state_agents.py` exists with a shebang, is committed mode 100755, and imports only the standard library plus `duckdb` (AST-checked).
- [ ] D02: the script carries a PEP 723 header (`requires-python >=3.11`, `dependencies = ["duckdb>=1.1.0"]`) and the documented invocation `uv run --no-project <script> bootstrap` works without any global install (empirically verified).
- [ ] D03: the schema is created idempotently: `features`, `contract_meta`, `contract_criteria`, `sprint_progress`, `execution_log` with the exact columns and CHECK constraints (3 statuses, 7 log types, 2 step categories) and integer PKs fed by sequences.
- [ ] D04: `bootstrap` succeeds twice in a row on the same database (idempotence, no error).
- [ ] D05: `migrate` runs in one transaction: a malformed source file rolls back, exits non-zero, leaves no data in the database and moves nothing.
- [ ] D06: `migrate` imports 100% of features from `feature_list.json` and `feature_list_archive.json`, tolerating both container shapes (`{"features": [...]}` and a bare list), preserving ids, names, descriptions and dependencies (`VARCHAR[]`).
- [ ] D07: an unknown feature status is coerced to `pending` with a printed warning instead of failing the migration.
- [ ] D08: `contract.md` criteria are extracted via the checkbox regex (bullets `-` and `*`, boxes `[ ]`/`[x]`/`[X]`) with `passed` mapped from the box state.
- [ ] D09: the test command is extracted from both the English format (`* Test command: ...`) and the legacy French format into `contract_meta.test_command`.
- [ ] D10: `progress.md` sections map to `objective` (Current Goal / French alias) and `milestone` (Iteration Milestones / French alias) with `done` mapped from the checkbox.
- [ ] D11: log entries are parsed from `docs/journal/log_*.md` (sorted by name) then `log.md`, with the strict 7-type regex tolerating padded separators, in exact chronological order (increasing ids).
- [ ] D12: `migrate` prints the count of skipped `## [` heading lines so no loss stays silent.
- [ ] D13: `--backup` moves `feature_list.json`, `feature_list_archive.json`, `contract.md`, `progress.md`, `log.md` and `docs/journal/` into `.agent/legacy_markdown_backup/` only after the transaction committed.
- [ ] D14: `--backup` appends `.agent/*.duckdb.wal` to the target `.gitignore` only when the line is absent.
- [ ] D15: `bootstrap` auto-runs `migrate --backup` when the database is absent and legacy files are detected.
- [ ] D16: `bootstrap` lists only active features (`status != 'completed'`).
- [ ] D17: `bootstrap` shows exactly the last 20 `execution_log` entries whatever the total.
- [ ] D18: `log` validates the type against the 7 types, warns above 200 characters, and still records the entry.
- [ ] D19: `feature add`/`status` validate ids (duplicate, unknown) and statuses; `step add`/`done`/`reset` manage the sprint table; `contract add`/`pass`/`cmd` manage the contract tables.
- [ ] D20: `search-log` filters with ILIKE and honors `--limit`.
- [ ] D21: `export-md` writes `.agent/DASHBOARD.md` summarizing the current state.
- [ ] D22: the `agent-state` skill is registered in `skills.json` (authored, MIT) and `skills/agent-state/scripts/state_agents.py` is byte-identical to `scripts/state_agents.py` (test-enforced).
- [ ] D23: the kit dogfood install `.agents/skills/agent-state/` is fingerprint-clean (`skills check .`).
- [ ] D24: canon v3.0 is registered, under 8192 bytes, resynced byte-identically into the kit `AGENTS.md` and the template; CHANGELOG documents the fleet migration order (skill before canon).
- [ ] D25: `sync_agents.py init --ledger` no longer writes legacy files (creates `.agent/` and prints the bootstrap command); `ledger` detects `.agent/state.duckdb`; the fleet CI command lines are unchanged.

## Evaluation Protocol

* Test command: `uv run --no-project --with "duckdb>=1.1.0" python -m unittest discover -s tests -v`
* Expected behavior: zero failures, plus `uvx ruff@0.16.9 check scripts tests` green and both `sync_agents.py check .` invocations green.
