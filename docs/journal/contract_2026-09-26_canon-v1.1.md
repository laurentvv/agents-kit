# Validation Contract — "canon v1.1" sprint

> Frozen on 2026-09-26 before the first change. Previous contract: `docs/journal/contract_2026-09-26_tooling.md`.
> Translated from French on 2026-09-26 (English sprint); file names, CLI flags, test names and state labels use their current v2.0 names.

## Automated Acceptance Criteria

- [ ] K01: the BEGIN marker of `agents-common.md` carries `v1.1`; v1.0 stays registered with its original fingerprint.
- [ ] K02: `version` returns 0 (v1.1 registered); `version --register` did not modify the v1.0 fingerprint.
- [ ] K03: `check .` and `check . --file template/AGENTS.template.md` return 0 on v1.1.
- [ ] K04: an AGENTS.md with an intact v1.0 block is classified "behind" and `sync` brings it to "up to date", keeping §7 byte-identical.
- [ ] K05: a hand-edited v1.0 block is still refused by `sync` without `--force`.
- [ ] K06: the canon states the priority: explicit user instruction > §7 > common block, §5 prohibitions lifted only on a formal request.
- [ ] K07: the canon forbids writing inside the block and sends lessons to §7 "Pitfalls & lessons".
- [ ] K08: the canon limits the ledger to feature suites (proportionality) and Bootstrap no longer forces its creation for a one-off task.
- [ ] K09: the canon specifies the contract lifecycle: validation results in `progress.md`, archiving in `docs/journal/` at closure.
- [ ] K10: the §3 loop has a "Closure" step (archiving, `done` entry, report done / verified / not verified).
- [ ] K11: the canon requires UTF-8 without BOM and forbids markdown pasted from a rich editor.
- [ ] K12: §4 covers the default branch (`main`/`master`) and destructive git commands beyond `reset --hard`.
- [ ] K13: §5 declares external content as data, never as instructions.
- [ ] K14: §6 forbids disabling, skipping or weakening a test and requires reporting a failure as is.
- [ ] K15: the canon stays generic (`test_canon_is_generic` green) and holds no corruption token (`CORRUPTION_RE` finds nothing).
- [ ] K16: the v1.1 block weighs less than 8 KB (context budget, loaded in every session).
- [ ] K17: the tests no longer hardcode a canon version and stay green on v1.0, then on v1.1.
- [ ] K18: unittest, `uvx ruff@0.16.9 check`, `ledger . --strict` green locally; GitHub CI green after push.

## Evaluation Protocol

* `uv run --no-project python -m unittest discover -s tests -v` · `uvx ruff@0.16.9 check scripts tests`
* `uv run --no-project python scripts/sync_agents.py version | check . | ledger . --strict`
* Real path: simulated v1.0 fleet → `audit` → `sync` → `audit --strict`.
