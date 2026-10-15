# Validation Contract — "skills updates" sprint

> Frozen before the first line of code (2026-09-28). Scope change = new contract approved by the user.

## Automated Acceptance Criteria

- [ ] C01: `skills update` checks every vendored skill against its upstream source (resolve current commit + fetch tarball; GitHub seam mocked in tests).
- [ ] C02: upstream unchanged and kit copy intact → "up to date", nothing written.
- [ ] C03: upstream moved with new content → vendored copy replaced, registry entry refreshed (ref, files, license, `updated` date); no `--force` needed for a clean kit copy.
- [ ] C04: a hand-edited kit copy (≠ skills.json) refuses the update without `--force`; `update --force` re-imports upstream over it.
- [ ] C05: a new upstream commit with identical content only moves the pin (files untouched, registry ref updated).
- [ ] C06: `update --skill NAME [--ref REF]` limits the check to one skill with an explicit ref; `--ref` without `--skill` is an input error (exit 2).
- [ ] C07: `update --dry-run` prints the plan (changed/removed files, re-pins, refusals) and writes nothing (network reads only).
- [ ] C08: an upstream failure on one skill (network, 404) is reported, the other skills still update, exit 1.
- [ ] C09: `skills deploy [root]` applies pending changes to every `<root>/<repo>` that already has `.agents/skills` (install/update/prune per skill), one line per repo, summary at the end.
- [ ] C10: repos without `.agents/skills` are skipped; `--exclude PATTERN` and `<root>/.agents-kit-ignore` are honored.
- [ ] C11: a hand-edited repository is refused (nothing written there), the rest of the fleet still deploys, exit 1.
- [ ] C12: `deploy --dry-run` prints the whole-fleet plan and writes nothing.
- [ ] C13: `deploy --strict` exits 1 unless every repo ends up to date (excluded ones excepted).
- [ ] C14: `deploy --skill NAME` limits the deployment to one skill.
- [ ] C15: no traceback on input/encoding errors; the unit tests stay offline (urlopen poisoned); the single-repo `sync` output is unchanged by the refactor.
- [ ] C16: `uvx ruff@0.16.9 check scripts tests` green; the whole suite green (72 pre-existing + new tests); `sync_agents.py` untouched; docs updated (README, CHANGELOG, §7) with the common block unchanged.
- [ ] C17: real-path validation executed and archived in progress.md: `skills update --dry-run` online against obra/superpowers, then `skills deploy --dry-run` over the fleet.

## Evaluation Protocol

* Test command: `uv run --no-project python -m unittest discover -s tests`
* Lint: `uvx ruff@0.16.9 check scripts tests`
* End to end: real `skills update --dry-run` (network) and `skills deploy --dry-run` (fleet, read-only).
* Expected behavior: every criterion backed by executed commands (exit codes) or file contents, recorded in progress.md.
