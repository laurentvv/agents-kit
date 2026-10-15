# Validation Contract — v1.1 "tooling" sprint

> Frozen on 2026-09-26 before the first line of code. The common block stays at v1.0: no content change.
> Translated from French on 2026-09-26 (English sprint); file names, CLI flags, test names and state labels use their current v2.0 names.

## Automated Acceptance Criteria

- [ ] C01: `audit` on a root holding a non-UTF-8 AGENTS.md ends with exit 0 and classifies that file as "unreadable".
- [ ] C02: a UTF-8 AGENTS.md with a BOM is read as without BOM ("up to date" if the block is identical).
- [ ] C03: `init` into a missing folder returns exit 2 with a message, no traceback.
- [ ] C04: `agents-common.versions.json` exists and the sha256 fingerprint of v1.0 matches the current canon.
- [ ] C05: a block identical to the canon is "up to date"; an intact older registered version is "behind".
- [ ] C06: a block with the same version but an unknown fingerprint is "hand-edited".
- [ ] C07: a block with a version higher than the canon is "ahead".
- [ ] C08: two BEGIN/END blocks in one file, or a BEGIN without END, are "invalid markers".
- [ ] C09: a marker quoted in a sentence (not at the start of a line) is not taken for a marker.
- [ ] C10: `sync` on a "hand-edited" or "ahead" block refuses (exit 1) without `--force` and writes nothing.
- [ ] C11: `sync --force` on an edited block replaces the block and keeps §7 byte-identical.
- [ ] C12: `sync` on an up-to-date file does not write (content and mtime unchanged).
- [ ] C13: `sync --dry-run` shows a unified diff and does not modify the file.
- [ ] C14: `check --diff` shows the diff between the installed block and the canon.
- [ ] C15: `sync`, `init` and `adopt` refuse (exit 2) to distribute a canon whose fingerprint is not registered.
- [ ] C16: `version` returns 0 if the canon is registered, 1 otherwise; `--register` refuses to rewrite the fingerprint of an already published version.
- [ ] C17: `audit` classifies as "excluded" the folders listed in `<root>/.agents-kit-ignore` or given with `--exclude`.
- [ ] C18: an AGENTS.md holding a Next.js/OpenSpec block AND project content is classified "to migrate"; a purely generated file stays "generated".
- [ ] C19: `audit --strict` returns 1 as soon as a file is neither up to date, generated nor excluded.
- [ ] C20: `adopt` inserts the block after the H1 title (and after a leading generated block), every original line is still present, `check` then returns 0.
- [ ] C21: `adopt` refuses an already managed file (exit 2).
- [ ] C22: `ledger` on a valid ledger returns 0; invalid JSON, duplicate id or missing file return 1.
- [ ] C23: `ledger` warns about: non-standard status, unarchived `completed`, log entry > 200 characters, entry outside the current month, unknown type, number of criteria outside 15-30.
- [ ] C24: the script stays standard-library only (no import outside the standard library), Python 3.11+.
- [ ] C25: `check .` and `check . --file template/AGENTS.template.md` return 0.
- [ ] C26: `uv run --no-project python -m unittest discover -s tests` green; `ruff check` green.
- [ ] C27: a GitHub Actions workflow runs the tests + kit checks on Ubuntu and Windows.

## Evaluation Protocol

* Test command: `uv run --no-project python -m unittest discover -s tests -v`
* Static checks: `uvx ruff check scripts tests` · `python -m py_compile scripts/sync_agents.py`
* Expected behavior: zero failures; the real path (CLI) is exercised on a simulated fleet on top of the tests.
