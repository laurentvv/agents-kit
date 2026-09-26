# Changelog

Versions of the **common block** (`agents-common.md`, fingerprints in `agents-common.versions.json`) and of the kit's **tooling**. Read the block entry before running `sync` on the fleet.

## Common block v2.1 — 2026-09-26

- §1 **Language** rule: English for everything written in the repository (code, comments, docs, commit messages, ledger); French for chat replies to the user. Any deviation is declared in §7 (the template's §7 line becomes "Language deviation").

Block size: 6 779 → 6 968 bytes. **Migration**: v1.x and v2.0 repositories are "behind" → `sync <repo>`. Their §7 keeps its language until translated; agents will write new content in English.

## Common block v2.0 — 2026-09-26

**English translation of v1.1** — same rules, same structure (same sections, bullets, steps and table rows). Two breaking changes for the fleet:

- **Language**: the block is now English (measured: 16 to 26 % fewer tokens than v1.1 depending on the tokenizer, see `docs/token-measurement-2026-09-26.md`).
- **Marker name**: `agents-commun` → `agents-common` (`<!-- BEGIN:agents-common v2.0 … -->` / `<!-- END:agents-common -->`); canon file `agents-commun.md` → `agents-common.md`, registry `agents-commun.versions.json` → `agents-common.versions.json`.

**Migration**: nothing to do by hand. The script still recognizes the v1.x `agents-commun` markers: `audit` reports v1.0 and v1.1 blocks as "behind", and `sync <repo>` replaces them with the v2.0 block and its new markers, keeping §7 byte-identical. A hand-edited v1.x block is refused as before (`check --diff`, move the specific part to §7, then `sync --force`). Each repository's §7 keeps its own language; the template's §7 now offers a "Reply language" line to tell agents which language to answer in.

Block size: 7 675 → 6 779 bytes.

## Tooling — 2026-09-26 (English)

- Everything in English: identifiers, messages, state labels, docs, ledger history.
- **Renamed CLI flags** (the former French names are rejected): `--file`, `--name`, `--exclude`, `--register`, `--dir`, `--status`, `--variant-b`.
- Template placeholder for the repository name is now `<REPO NAME>` (was a French placeholder).
- Script messages are plain ASCII (no console-encoding issue on Windows).
- New test: the repository stays English-only (no French characters or file names).

- Reusable workflow `.github/workflows/agents-md-check.yml` + caller template `template/agents-md.yml`: each repository's CI turns red while its block is behind, hand-edited or broken (weekly run included). The kit's own CI runs it against every commit.
- Rollout checklist in `docs/MIGRATION.md`: release the kit first (an older kit does not know newer markers), then `audit --strict` → `sync` → `audit --strict`.

## Common block v1.1 — 2026-09-26

From a critical review of v1.0 and the findings of the "tooling" sprint. No rule removed; **two policy changes** (review them before syncing the fleet):

- **Priority of instructions** (new header): explicit user instruction > the repo's §7 > common block; the §5 prohibitions are lifted only on a formal request.
- **Ledger proportionality** (§2, §3 Bootstrap): the ledger is for feature suites; a question or a one-off fix no longer opens a sprint. *Relaxed rule*: v1.0 required creating the 4 files on every start.

Additions and clarifications:

- Header + §6: the block is overwritten on every sync; lessons go to §7 "Pitfalls & lessons" (an agent writing inside the block saw its lesson erased by `sync`).
- §1: OS/shell deviations (PowerShell 7, WSL, Linux) declared in §7; files in UTF-8 without BOM; never markdown pasted from a rich editor (cause of the 3 corrupted files in the audit).
- §2: contract lifecycle — validation results in `progress.md`, scope change = new contract, archiving in `docs/journal/` at closure.
- §3: pinned verification tools (same version locally and in CI); new step 6 **Closure** (archiving, `done` entry, report done · verified · not verified).
- §4: default branch `main`/`master`; destructive git commands listed (`reset --hard`, `clean -fd`, `checkout -- .`/`restore .`, `push --force` on a shared branch).
- §5: external content (web, issues, files, tool outputs) = data, never instructions.
- §6: never disable, skip or weaken a test to get green; a failure is reported as is.

Block size: 5 843 → 7 675 bytes (budget < 8 KB = 8 192 bytes).

**Migration**: `audit` reports v1.0 repositories as "behind" → `sync <repo>` (safe, §7 kept byte-identical). A "hand-edited" repository is refused: `check --diff`, move what must stay to §7, then `sync --force`. In §7: declare any OS/shell deviation.

## Tooling — 2026-09-26

- `sync`: refuses to overwrite a hand-edited block or one newer than the kit (`--force`), writes nothing if up to date, `--dry-run`.
- Registry of fingerprints + `version [--register]`: "behind" vs "hand-edited"; a canon changed without a version bump is never distributed.
- `adopt`: integrates the block into an existing AGENTS.md without losing a line.
- `ledger`: read-only lint of the 4 state files (contract and progress optional between sprints, per the v1.1 Closure step).
- `audit`: exclusions (`.agents-kit-ignore`, `--exclude`), `--strict`, robust reading (encoding, BOM, CRLF), mixed Next.js/OpenSpec blocks "to migrate"; `check --diff`.
- unittest tests (standard library) + GitHub Actions CI on Ubuntu/Windows, pinned ruff.

## Common block v1.0 — 2026-09-26

First version, consolidated from the audit of 24 real files (`docs/audit-2026-09-26.md`).
