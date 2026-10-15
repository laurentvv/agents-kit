# Sprint Progress — "skills management"

## Current Goal
- [x] Common skills managed by the kit: import once from GitHub, deploy to every repository's `.agents/skills/`, detect drift, update the fleet.

## Iteration Milestones
- [x] F-16: `skills add` / `skills list` (vendoring + skills.json registry)
- [x] F-17: `skills sync` / `skills check` (deploy + lock + refusals)
- [x] F-18: `skills audit` (fleet sweep)
- [x] F-19: offline test suite (mocked GitHub seam)
- [x] F-20: docs + first real skill vendored end to end

## Contract Validation

All 22 criteria validated on 2026-09-28 (branch `feat/skills-management`):

- [x] C01: `test_vendors_files_and_registers` (mocked tarball) + real `skills add` of `using-superpowers` — exit 0, 8 files under `skills/using-superpowers/`.
- [x] C02: `skills.json` after the real import: `source: obra/superpowers`, `ref: 8ca22db…` (40-hex), `imported: 2026-09-28`, 8 per-file sha256 entries.
- [x] C03: `test_new_upstream_refused_then_force_replaces` — exit 1 `REFUSED` (registry bytes unchanged), then `--force` → 0, files and ref replaced.
- [x] C04: `test_ref_resolved_and_sha_passthrough` — `resolve_ref` called with `(slug, None)` and `(slug, "v1.2.3")`; a 40-hex ref passes through the real function with urlopen poisoned.
- [x] C05: `test_hand_edited_kit_copy_refused_without_force` — exit 1 with "hand-edited", kit file intact; `--force` → 0.
- [x] C06: `skills list` prints `using-superpowers  obra/superpowers@8ca22dba9a94  8 file(s)  imported 2026-09-28  license MIT`.
- [x] C07: `test_installs_and_writes_the_lock` + real `sync` into a temp copy of fire_UI: files installed, `.agents-kit.json` written with source/ref/fingerprints.
- [x] C08: `test_up_to_date_writes_nothing` — skill file and lock mtimes unchanged (1 000 000 000), exit 0.
- [x] C09: `test_behind_is_updated` — kit moved to SHA2/BODY2, `sync` → 0, installed body v2, lock ref SHA2.
- [x] C10: `test_hand_edited_refused_then_force` — exit 1, local edit preserved, nothing written; `--force` → 0 then `check` → 0.
- [x] C11: `test_dry_run_writes_nothing` — plan printed (`+ SKILL.md`), "Dry run", bytes unchanged.
- [x] C12: `test_single_skill_filter` — only `other` installed; `using-x` absent.
- [x] C13: `test_exit_codes` — 2 (nothing installed), 1 (missing skill, "install" shown), 0 (UP TO DATE).
- [x] C14: `test_sweep_strict_and_exclusions` — up to date / behind / hand-edited listed; `--strict` 1; `--exclude` and `.agents-kit-ignore` honored (→ 0); `test_repos_without_skills_are_skipped`.
- [x] C15: `test_orphan_is_pruned` — dry-run lists the orphan, `sync` removes the folder and empties the lock.
- [x] C16: `test_non_utf8_lock_and_registry_no_traceback` — exit 2 `INVALID LOCK` / `INVALID REGISTRY`, no traceback.
- [x] C17: `urlopen` poisoned with AssertionError in `Kit.setUp`: the whole suite (72 tests) passes offline.
- [x] C18: `test_stdlib_only` (AST, stdlib + sync_agents only); `sync_agents.py` untouched (`git diff` empty on the file); `test_sync_agents_surface_unchanged` proves the fleet CI command line still works.
- [x] C19: `uvx ruff@0.16.9 check scripts tests` → "All checks passed!"; suite: 72 tests OK (the 50 pre-existing included).
- [x] C20: the English-only guard tests pass unchanged (included in the 72).
- [x] C21: README section "Common skills", CHANGELOG entry "Tooling — 2026-09-28", kit AGENTS.md §7 (mission, commands, invariant); `sync_agents.py check .` still UP TO DATE (v2.1) — common block untouched, no version bump.
- [x] C22: real `skills add https://github.com/obra/superpowers --skill using-superpowers` → exit 0 (commit `8ca22dba9a94…`, 8 files, license MIT); real `sync` + `check` + `audit` on a temp copy of fire_UI: 0 / 0 / 0, SKILL.md and lock present.

## Evaluation Protocol

* Tests: `uv run --no-project python -m unittest discover -s tests` → Ran 72 tests, OK.
* Lint: `uvx ruff@0.16.9 check scripts tests` → All checks passed.
* End to end: real `skills add` (network) then `skills sync`/`check`/`audit` on a temp copy of fire_UI → all exit 0.
