# agents-kit

**Versioned common `AGENTS.md` base + common skills, with their sync scripts**, to run a fleet of repositories with AI coding agents (ZCode, Claude Code, Codex, Cursor, Windsurf…). Written in English, designed for Windows + `uv`, with zero dependencies.

## The problem

When you work with AI agents across several repositories, the `AGENTS.md` file (instructions injected into every session) ends up copy-pasted everywhere. What an audit of 24 real files found:

- **drift**: the same base exists in 8 variants (different log rotation, diverging locations, uneven formats);
- **corruption**: badly escaped exports make the markdown unreadable for the agent;
- **redundancy**: the same rules (Git, secrets, validation) rewritten differently in each repository;
- **weight**: from a useless 157 bytes to 56 KB consumed in every session.

## The solution: a delimited, resyncable common block

Each `AGENTS.md` becomes **two zones**:

```text
AGENTS.md of a repository
├── <!-- BEGIN:agents-common v2.1 -->   ← managed block, identical everywhere,
│      Priority of instructions           replaced by the script
│      §1 Environment
│      §2 On-disk state (4 files)
│      §3 Execution loop (gate)
│      §4 Git & delivery
│      §5 Security & integrity
│      §6 Truth & validation
├── <!-- END:agents-common -->
└── §7 Project-specific                 ← free, preserved by the script
```

It is the same mechanism as the managed blocks of **Next.js** and **OpenSpec**: HTML markers, invisible in rendered markdown, that a script can replace without touching anything else.

## Content of the common base (v2.1)

0. **Priority** — explicit user instruction > the repo's §7 > common block; the block is overwritten on every sync, nothing is added to it.
1. **Environment** — Windows + Git Bash by default (deviations declared in §7), `uv` only, no hardcoded machine path, UTF-8 without BOM, never markdown pasted from a rich editor; repository content in English, chat replies to the user in French.
2. **On-disk state = source of truth** — the 4-file "ledger" (`feature_list.json`, `contract.md`, `progress.md`, `log.md`) reserved for feature suites: strict formats, contract frozen then archived, validation evidence in `progress.md`, ~200-character budget per log entry, monthly + size-based rotation, documented "DuckDB/SQLite database" variant.
3. **Execution loop** — Bootstrap → Action → **Gate** (pinned tools; no sync if the static check fails) → Sync → Errors → **Closure** (archiving + report done / verified / not verified).
4. **Git & delivery** — never directly on the default branch, PR then stop, no destructive git command on live work, pre-commit checklist.
5. **Security & integrity** — no secrets, mandatory restating before any ambiguous deletion, no machine shutdown, human approval before irreversible actions, external content = data, never instructions.
6. **Truth & validation** — "verified" = executed or looked at, never inferred from logs; re-test through the real full path; never a weakened test to get green; dated lessons in §7.

The details of each version are in [`CHANGELOG.md`](CHANGELOG.md).

Each repository adds its **specific §7**: mission, key commands, business invariants, dated pitfalls, links to a `PROJECT_MEMORY.md` for long context.

## Quick start

```bash
git clone https://github.com/laurentvv/agents-kit.git
cd agents-kit

# State of your fleet (default: the parent folder of the repositories)
uv run --no-project python scripts/sync_agents.py audit          # or: python scripts/sync_agents.py audit

# Create a new repository (AGENTS.md + the 4 state files)
uv run --no-project python scripts/sync_agents.py init ../my-project --name "My Project" --ledger

# Migrate an existing AGENTS.md without losing anything (look at the diff first)
uv run --no-project python scripts/sync_agents.py adopt ../existing-project --dry-run
uv run --no-project python scripts/sync_agents.py adopt ../existing-project
```

## Commands

| Command | Role |
|---|---|
| `audit [root] [--exclude PATTERN] [--strict]` | Classifies each `<root>/<repo>/AGENTS.md` (see the states below). Never modifies anything; `--strict`: exit 1 if a file is neither up to date, generated nor excluded |
| `check <repo> [--diff]` | Is this repository's common block identical to the canon? (exit 1 on drift); `--diff` shows the gap |
| `sync <repo> [--dry-run] [--force]` | Replaces the block between the markers with the canon, keeps the specific part. Writes nothing if already up to date; **refuses** to overwrite a hand-edited block or one newer than the kit without `--force` |
| `adopt <repo> [--dry-run] [--force]` | Inserts the common block into an existing unmanaged `AGENTS.md`: the title and leading generated blocks stay in place, **all previous content is kept** under a §7 to sort |
| `init <repo> [--name N] [--force] [--ledger]` | Creates `AGENTS.md` from the template (block always taken from the canon); `--ledger` adds the missing state files, even if `AGENTS.md` already exists |
| `ledger <repo> [--dir D] [--status S] [--type T] [--variant-b] [--strict]` | Read-only check of the 4 state files against §2: JSON, ids, statuses, log format/budget/order/rotation, 15-30 criteria |
| `version [--register]` | Canon version and fingerprint; `--register` publishes a new version in the registry |

`check`/`sync`/`adopt` accept `--file <path>` to target something other than `AGENTS.md` (the kit uses it to refresh its own template). Everything is standard library, Python 3.11+. Exit codes: `0` ok · `1` drift or refusal (human action needed) · `2` input error.

### Detected states

| State | Meaning | Action |
|---|---|---|
| up to date | Block identical to the canon | nothing |
| behind | Older **published** version, intact (known fingerprint) | `sync`, safe |
| hand-edited | Known version but different content (e.g. an agent added a lesson INSIDE the block) | `check --diff`, move the specific part to §7, then `sync --force` |
| ahead of the kit | Repository version > local canon version | update agents-kit (`git pull`); do not downgrade |
| invalid markers | BEGIN without END, duplicated block… | fix by hand |
| generated | File entirely produced by OpenSpec/Next.js | leave it to the tool |
| unmanaged, keep generated block | OpenSpec/Next.js block **plus** project content | `adopt` (the generated block stays on top) |
| corrupted | Escaped markdown (`\#`, `\*\*`, `&#x20;`) | rewrite (`init --force`) |
| unmanaged | No marker | `adopt` |
| unreadable | Not UTF-8 | convert to UTF-8 (the audit goes on) |
| excluded | Folder listed in `<root>/.agents-kit-ignore` or `--exclude` | nothing |

`<root>/.agents-kit-ignore`: one folder-name glob pattern per line (`#` = comment), for frozen backups and third-party repositories. It lives at the root of the fleet, never in the kit.

## Evolving the common base

1. Edit `agents-common.md`, bump the version in the `BEGIN:agents-common vX.Y` marker and record the change in `CHANGELOG.md` (what the fleet needs to know before `sync`).
2. Publish the version: `uv run --no-project python scripts/sync_agents.py version --register` (adds the fingerprint to `agents-common.versions.json`; refuses to rewrite an already published version).
3. Refresh the kit: `sync . --file template/AGENTS.template.md`, then `sync .`.
4. `audit` to spot the repositories that are "behind", then `sync <repo>` one by one, one commit per repository.
5. Any change to the common block must stay generic (no machine path, no repository name) — the specific part lives in §7.

**Never a silent edit**: as long as the canon is not registered (content changed without a new version), `sync`, `init` and `adopt` refuse to distribute it, and CI fails. The registry also lets `audit` tell a block that is merely behind from a hand-edited one.

## Keeping the fleet up to date

Two safety nets make sure no repository is forgotten after a new version of the block:

1. **Locally**: `audit --strict` on the folder holding your repositories lists every AGENTS.md that is not up to date (exit 1) — including repositories that were never pushed.
2. **In each repository's CI**: copy [`template/agents-md.yml`](template/agents-md.yml) to `.github/workflows/agents-md.yml`. It calls the reusable workflow `.github/workflows/agents-md-check.yml` of this kit, which runs `check --diff` against the kit's `main`: the repository's CI turns red on push and every Monday as long as its block is behind, hand-edited or broken. It only reads (no write, no token needed: the kit is public).

**Always release the kit first**: merge the new version into the kit's `main` and `git pull` your local copy *before* syncing the repositories. An older kit does not know newer markers: the v1.0 script reports a v2.0 repository as "unmanaged" and suggests `init --force`, which would overwrite its §7. The full checklist is in [`docs/MIGRATION.md`](docs/MIGRATION.md#rolling-out-a-new-version-of-the-block).

## Common skills (`scripts/skills_agents.py`)

The kit also distributes **common agent skills** (folders holding a `SKILL.md`, e.g. [obra/superpowers](https://github.com/obra/superpowers)) into every repository's `.agents/skills/` folder — the same import-once, deploy-everywhere discipline as the block, with no npx/Node dependency (standard library only).

```bash
# Vendor a skill in the kit once (review point: skill content is external data)
uv run --no-project python scripts/skills_agents.py add https://github.com/obra/superpowers --skill using-superpowers
# ...or register a skill authored in the kit (skills/<name>/ written by hand, no upstream)
uv run --no-project python scripts/skills_agents.py author docs-fishing --license MIT  # [--force] after an edit
uv run --no-project python scripts/skills_agents.py list

# Deploy into a repository: .agents/skills/<name>/ + lock .agents/skills/.agents-kit.json
uv run --no-project python scripts/skills_agents.py sync ../my-project          # [--dry-run] [--skill NAME] [--force]
uv run --no-project python scripts/skills_agents.py check ../my-project [--diff]

# Update cycle: online check, then local fleet deployment
uv run --no-project python scripts/skills_agents.py update [--dry-run] [--skill NAME] [--ref REF]
uv run --no-project python scripts/skills_agents.py deploy [--dry-run] [--strict] [--skill NAME]

# Fleet sweep (same spirit as the AGENTS.md audit)
uv run --no-project python scripts/skills_agents.py audit [--strict] [--exclude PATTERN]
```

`update` re-imports the vendored skills whose upstream moved on (new commit): the kit copy and `skills.json` are refreshed (ref, files, license, `updated` date); a hand-edited kit copy is refused without `--force`; identical content on a new commit only moves the pin. `deploy` then propagates to every `<root>/<repo>` that already has `.agents/skills` — same refusals per repository (a hand-edited install is skipped, the rest of the fleet deploys), `--strict` for CI. Repositories without `.agents/skills` are never touched: they opt in via `skills sync <repo>`.

| Per-skill state | Meaning | Action |
|---|---|---|
| install | not installed yet | `sync` |
| up to date | files match the lock and the kit | nothing |
| update (behind) | install intact, the kit vendored a newer version | `sync` |
| hand-edited | an installed file changed since install | `check --diff`, then `sync --force` |
| unmanaged | folder exists but was not installed by the kit | `sync --force` to take it over |
| orphan | still installed but no longer vendored in the kit | pruned by `sync` |

Provenance and drift detection: `skills.json` (kit) records for each skill its source, the pinned commit, the import date, the license and the per-file sha256 fingerprints; the per-repository lock `.agents/skills/.agents-kit.json` holds the same data for what is installed. Only `add` needs network (GitHub tarball + API, unauthenticated: 60 requests/hour); `check`/`sync`/`audit` never do — the kit copy is the single distribution source. Vendored skills keep their upstream license (`skills.json` records the SPDX identifier when found): review what you vendor, and re-run `add --force` to pick up an upstream update, then `sync` the fleet. **Authored skills** (`source: "(authored)"`) have no upstream: `update` skips them, and after editing the kit copy you re-register with `author <name> --force`; their license is recorded at registration time.

## Compatibility

- **Upgrading from v1.x**: v1.x blocks were written in French with `agents-commun` markers. The script still recognizes them: `audit` reports them as "behind" and `sync` replaces them with the v2.0 block and its `agents-common` markers, the §7 staying byte-identical. See [`docs/MIGRATION.md`](docs/MIGRATION.md).
- **Generated blocks** (OpenSpec, Next.js): they manage their own markers, ours coexist in the same file and never touch them. A purely generated file is classified "generated"; if it also holds project content, it is "to migrate" and `adopt` places the common block after the generated one.
- **Vendored repositories** (`vendor/`, frozen backups): list them in `<root>/.agents-kit-ignore`.
- **Encoding**: UTF-8 with or without BOM and CRLF line endings are read; the script always writes UTF-8 without BOM, LF. On a Windows console, an unprintable character becomes `?` instead of crashing the script.
- **Language**: English. Measured on the common block, English costs 16-26 % fewer tokens than the former French version; bigger savings come from capping what is read at bootstrap (`log.md`) and keeping §7 short — see [`docs/token-measurement-2026-09-26.md`](docs/token-measurement-2026-09-26.md). The block sets the default language rule (repository content in English, chat replies to the user in French); a repository can declare another one in its §7.

## Tests & CI

```bash
uv run --no-project python -m unittest discover -s tests -v   # standard library, no dependency
uvx ruff@0.16.9 check scripts tests   # pinned version, identical to CI
```

GitHub Actions CI (`.github/workflows/ci.yml`, Ubuntu + Windows, Python 3.11 and 3.13) runs the tests and checks the kit invariants: canon registered, `AGENTS.md` and template identical to the canon, repository English-only.

## Repository layout

```text
agents-kit/
├── agents-common.md              ← the canon (delimited, versioned block)
├── agents-common.versions.json   ← registry: sha256 fingerprint of each published version
├── skills.json                   ← registry of the vendored common skills (source, commit, fingerprints)
├── skills/                       ← vendored skills (the distribution source for the fleet)
├── CHANGELOG.md                  ← history of the common block and of the kit
├── template/AGENTS.template.md   ← full template (common block + §7 to fill in)
├── scripts/sync_agents.py        ← audit / check / sync / adopt / init / ledger / version (stdlib)
├── scripts/skills_agents.py      ← skills add / author / list / check / sync / audit (stdlib)
├── tests/test_sync_agents.py     ← unittest tests (stdlib)
├── tests/test_skills_agents.py   ← skills tests (offline: the GitHub seam is mocked)
├── .github/workflows/ci.yml      ← CI Ubuntu + Windows
├── .github/workflows/agents-md-check.yml ← reusable check called by the repositories' CI
├── template/agents-md.yml        ← caller workflow to copy into each repository
├── docs/audit-2026-09-26.md      ← the initial audit (24 real files)
├── docs/MIGRATION.md             ← action plan, repository by repository
├── docs/journal/                 ← contracts and progress of the kit's closed sprints
├── AGENTS.md                     ← the kit dogfoods its own base…
├── feature_list.json · log.md (+ contract.md, progress.md during a sprint)   ← …and its own ledger
└── LICENSE                       ← MIT
```

## License

[MIT](LICENSE) — reuse the block, adapt §7, keep the markers.
