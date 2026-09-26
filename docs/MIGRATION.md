# Migration plan for the repositories to agents-kit

From the audit of 2026-09-26 (`docs/audit-2026-09-26.md`). Repository names and file names below are proper names of existing repositories and are kept as they are. Every migration follows the same steps:

1. **`adopt <repo> --dry-run`, then `adopt <repo>`** as soon as there is content to keep: the common block is inserted after the title (and after a leading Next.js/OpenSpec block), all the previous content is kept under a §7 to sort — nothing is lost. `init <repo> --force` only for a corrupted or 100 % generic file;
2. sort §7: remove the old base now covered by the common block, keep the business content, move long context to `PROJECT_MEMORY.md` / `docs/`;
3. `check <repo>` green, `ledger <repo>` if the repository has a ledger, then `audit` to confirm;
4. one commit per repository (`chore: agents-kit v2.0 - common block + specific part`).

## Repositories already on v1.x

Repositories synced with v1.0 or v1.1 carry the French block and the `agents-commun` markers. `audit` reports them as "behind"; `sync <repo>` replaces the block with v2.0 (English, `agents-common` markers) and keeps §7 byte-identical. Their §7 stays in its own language until it is translated: from v2.1 the block itself asks agents to write the repository in English and to reply to the user in French.

## Rolling out a new version of the block

Checklist — follow it in this order for every new version (v2.0 included):

1. **Release the kit first**: merge the new version into the kit's `main`, then `git pull` the local copy of the kit. An older kit does not know newer markers (the v1.0 script calls a v2.0 repository "unmanaged" and suggests `init --force`, which would overwrite §7).
2. `audit --strict` on the folder of the repositories: the list of everything not up to date.
3. Every "behind" repository: `sync <repo> --dry-run`, then `sync <repo>`; commit on a `feat/…` or `fix/…` branch and open a PR, as the repository's own rules require.
4. Every "hand-edited" repository: `check <repo> --diff`, move what must stay to §7, then `sync <repo> --force`.
5. `audit --strict` again: **exit 0 = every local repository is up to date.**
6. Repositories with the CI guard (`template/agents-md.yml`): their CI goes back to green once synced; any repository forgotten stays red, including on GitHub-only repositories.

State on 2026-09-26 (GitHub): only `generator-assets` uses the block (v1.0, intact → "behind"); `lheritier-du-vide` has an unmanaged AGENTS.md (`adopt` candidate). Repositories that exist only locally are covered by step 2.

## Wave 1 — corrupted, duplicated and empty files (immediate gain)

| Repository | Action |
|---|---|
| `disk-clean` | Rewrite: common block + minimal §7 (mission, commands) — the current file is corrupted and 100 % generic |
| `compare-graph-generator` | Same as `disk-clean` (corrupted byte-identical duplicate) |
| `blender-ia` | Rewrite the corrupted file; keep the "verification before delivery" section (GPU HIP/CPU rendering, `blender_run.py --device`) in §7 |
| `Laya` | Replace the generic copy: common block + §7 (5-10 real lines) |
| `YouTubeToMP3` | Same as `Laya` (state the yt-dlp venv and the anti-bot cookies in §7) |
| `alerte-wti` | `init --ledger`, then fill in §7 (Windows env + `.venv` of trading_bot) |

## Wave 2 — base to replace, business content to keep

| Repository | Action |
|---|---|
| `web-assets` | `adopt`, then remove the outdated base (no rotation); §7: Scriptorium 8787, `data/app.db` database |
| `video-analys-ia` | Replace the base part; §7: §0 "final mission" (analyze → replicate), ecosystem |
| `roblox` | Replace the base (its improvements — 200-character budget, static gate, `awaiting_playtest` — are part of the common block since v1); §7: NotebookLM KB, asset hygiene, graphic standard |
| `L'HERITIER DU VIDE` (C:\test) | Split: generic spec → common block; Godot/pitfalls/3D/DuckDB assets/Fab business content → §7 (+ possibly `PROJECT_MEMORY.md` for long context) |

## Wave 3 — slimming and deduplication

| Repository | Action |
|---|---|
| `ai-doc2video` | Slim down (56 KB): move detailed TTS commands, OAuth protocol and playlists to `docs/memory_bank/`; §7 = compass + 26 tightened rules; ecosystem → single source shared with generator-assets |
| `generator-assets` | Extract the ecosystem map to the single source; §7: consumer contract, watch, update/rollback process |
| `fire_UI` | `adopt` (the Next.js block stays on top, the common block goes after the title); §7: declared PowerShell, frozen stack, `patrimoine.db` guard |

## Wave 4 — light alignment (already good)

| Repository | Action |
|---|---|
| `jardin-os` | Already follows the 2-level model — serves as the reference; `adopt` to add the block (the Next.js block stays on top), otherwise exclude it |
| `my-claw`, `ComfyUI-Majoor-OmniCam`, `Trading-AI` | Optional: `adopt` for Git/security/truth, keep their own structure in §7 — otherwise exclude them so that `audit --strict` stays green |
| `graph-orchestrator-smolagents` | Keep the DuckDB variant (documented as variant B of the common block); §7: factory/products scope; `ledger --variant-b` |

## Do NOT migrate

| Target | Reason |
|---|---|
| `pdf-ocr-ai` / `pdf-to-md-ocr` (root + `openspec/`) | OpenSpec managed blocks — `openspec update` only; never by hand |
| `Trading-AI/vendor/timesfm` | Vendored Google repository |
| `video-analys-ia_sauvegarde_etat_2026-09-16` | Frozen backup by design |

These exclusions are declared in `<root>/.agents-kit-ignore` (one folder-name glob pattern per line), at the root of the fleet and not in the kit, for example (the pattern matches the real backup folder name):

```text
# frozen backups
*_sauvegarde_*
```

(Pure OpenSpec repositories do not need to be listed: `audit` already classifies them as "generated"; `vendor/` being nested, `audit` does not walk it.)

## After migration

- `uv run --no-project python scripts/sync_agents.py audit --strict` returns 0: only "up to date" (managed repositories), "generated" (pure OpenSpec) and "excluded" remain.
- Any future change to the common block: edit `agents-common.md`, bump the version, `version --register`, resync the template and the kit's AGENTS.md, then `sync` repository by repository (a "hand-edited" repository is refused: `check --diff` first).
