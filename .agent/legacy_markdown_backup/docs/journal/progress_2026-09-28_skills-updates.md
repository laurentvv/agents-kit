# Sprint Progress — "skills updates"

## Current Goal
- [x] `skills update` (online: refresh the vendored copies from upstream) then `skills deploy` (local: propagate to every repository's .agents/skills).

## Iteration Milestones
- [x] F-21: `skills update` command
- [x] F-22: `skills deploy` command (fleet sweep, shared sync_repo with `sync`)
- [x] F-23: offline tests (87 green)
- [x] F-24: docs + real-path validation

## Contract Validation

All 17 criteria validated on 2026-09-28 (branch `feat/skills-management`):

- [x] C01: `test_upstream_moved_updates_the_vendored_copy` (resolve + tarball mocked) — the check runs against the recorded source of each vendored skill.
- [x] C02: `test_upstream_unchanged_is_up_to_date` — "up to date   using-x", registry bytes unchanged.
- [x] C03: `test_upstream_moved_updates_the_vendored_copy` — vendored body replaced, registry ref SHA2, `updated` = today, license kept; fleet `sync` picks the new body.
- [x] C04: `test_hand_edited_kit_copy_refused_then_force` — exit 1 REFUSED (file intact), then `--force` re-imports upstream (exit 0).
- [x] C05: `test_repin_when_content_identical` — "re-pin", ref moved to SHA2, file bytes untouched.
- [x] C06: `test_skill_and_ref_flags` (resolve called with `(slug, "v9.9")`, content updated) and `test_ref_without_skill_and_unknown_skill` (exit 2, "--ref requires --skill" / "UNKNOWN SKILL").
- [x] C07: `test_dry_run_writes_nothing` — plan printed (+ SKILL.md), "dry run: nothing written", registry and file bytes unchanged.
- [x] C08: `test_upstream_failure_isolated` — "FAILED other - GITHUB: HTTP 404", using-x still updated, exit 1.
- [x] C09: `test_fleet_states` — per-repo statuses up_to_date / applied / refused, one line each, summary; hand-edited repo untouched while the rest deploys.
- [x] C10: repos without `.agents/skills` skipped ("no-skills" absent from the output); `test_exclusions_and_strict` (—exclude and `.agents-kit-ignore` honored, strict exit 0 when the remainder is clean).
- [x] C11: `test_fleet_states` / `test_force_overwrites_the_refused_one` — refused repo left intact, fleet deploys, exit 1 (0 with `--force`).
- [x] C12: `test_dry_run_writes_nothing` (deploy) — plan printed, bytes unchanged.
- [x] C13: `test_dry_run_reports_up_to_date_repos_correctly` (regression for the dry-run status bug) + `test_exclusions_and_strict` — `--strict` exits 1 unless everything is up to date.
- [x] C14: `test_skill_filter` — only the named skill deployed.
- [x] C15: encoding errors stay clean messages (existing `Encoding` tests); `urlopen` poisoned in `Kit.setUp`, 87 tests green offline; single-repo `sync` output unchanged (all pre-existing Sync/Check/Audit tests pass untouched).
- [x] C16: ruff@0.16.9 "All checks passed!"; 87 tests OK (72 pre-existing + 15 new); `git status`: `sync_agents.py` untouched; README "Update cycle" paragraph, CHANGELOG bullets, kit §7 commands — `sync_agents.py check .` still UP TO DATE (v2.1).
- [x] C17: real paths executed (2026-09-28): `skills update --dry-run` → "up to date   using-superpowers (8ca22dba9a94)", exit 0 (live GitHub resolution); `skills deploy --dry-run` over C:\GIT → "Summary: 15 up_to_date, 2 applied, 1 refused" — the 2 "applied" are branch artifacts (trad-fr-to-en working tree on its feature branch; Trading-AI held back), the 1 "refused" is video-analys-ia's active WIP branch where the skill content drifts from the pin (deploy refuses without --force, by design). The dry-run initially reported every repo "applied" — a real status bug caught by this validation, fixed and covered by C13's regression test.

## Evaluation Protocol

* Tests: `uv run --no-project python -m unittest discover -s tests` → Ran 87 tests, OK.
* Lint: `uvx ruff@0.16.9 check scripts tests` → All checks passed.
* End to end: real `skills update --dry-run` (network, exit 0) and real `skills deploy --dry-run` (fleet read-only, truthful statuses after the fix).
