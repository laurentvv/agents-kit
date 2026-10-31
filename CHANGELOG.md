# Changelog

Versions of the **common block** (`agents-common.md`, fingerprints in `agents-common.versions.json`) and of the kit's **tooling**. Read the block entry before running `sync` on the fleet.

## Tooling — 2026-10-31: impeccable skill vendored (+ `--folder` selection flag)

- New vendored skill: **`impeccable`** (pbakaus/impeccable, Apache-2.0, pinned `b7a8917`, skill `0.1.18`) — the design toolkit for coding agents: 24 commands (`critique`/`audit`/`polish`/`bolder`/`quieter`/`animate`/`live`…), a craft floor of absolute bans, four visitor modes, PRODUCT.md/DESIGN.md capture, 4 sub-agent definitions, and a **62-rule deterministic slop detector** (no LLM, no API key; `npx impeccable detect --github` for CI stays an external npm dependency, llm-evals discipline). Vendored from the `.agents/skills/impeccable/` mirror: 63 files, 2.3 MB (font-index.json 1.1 MB, live-browser.js 550 KB); upstream NOTICE kept at `docs/upstream-notices/impeccable-NOTICE.md`.
- **New `skills add --folder PATH` flag**: the repository ships the same skill in two layout mirrors (`.agent/` light without sub-agents, `.agents/` full with hardcoded `.agents/…` prose paths); tar order silently picked the light one, whose paths are wrong for the fleet's `.agents/skills/` installs. The flag is validated against the tarball's candidate folders, recorded in `skills.json` (`folder` key) and honored by `update` on every re-import — 5 regression tests (`FolderSelection`). Backward compatible: pins without `folder` keep the first-candidate behavior.
- Supply-chain review (§5/§6) before vendoring: both launchers read in full — engine download only from the project's GitHub releases, **fail-closed** against the vendored `engine-checksums.txt` (no sha256 → no download), never pipes network content into a shell; no `child_process`/`eval`/exfiltration patterns across the 63 files; the Rust engine itself is NOT vendored and NOT fetched at vendor/deploy time (first-run download, `IMPECCABLE_BIN`/PATH preinstall for egress-free CI).
- Line endings: `impeccable.cmd` ships CRLF — `*.cmd`/`*.bat` now `-text` in `.gitattributes` (byte-exact; LF would break cmd.exe `goto` labels and drift fingerprints on fresh clones). **Fleet deploy note**: consuming repositories need the same `*.cmd -text` line in their own `.gitattributes` (checklist in the audit doc).
- Audit, routing guidance (impeccable owns the design workflow; the taste cluster stays the aesthetics references) and deploy checklist: `docs/impeccable-skills-2026-10-31.md`.

## Tooling — 2026-10-30: on-demand skills refresh (6 content updates, 5 re-pins)

- User-triggered cycle (the anonymous-API dry-run died on 403 after ~60 calls — 8 false failures, among them 5 skills actually unchanged; recovery identical to the 2026-10-22/10-29 notes: upstream HEADs resolved via authenticated `gh api` outside the REST quota, then `update --skill <name> --ref <sha>` per skill). **11 skills moved, 0 refused.**
- Content updates: **blender pack** `71d031da` → `fb92cfb4` (EL4CTEO/blender-skills, skills at version `1.1.0` → `1.2.0`): `blender-core` SKILL.md routing table gains 6 new sibling rows (`blender-texturing`, `blender-clothing`, `blender-hair-grooming`, `blender-stylized-npr`, `blender-environment-kits`, `blender-video-editing` — **not vendored**, deliberate-subset situation identical to the unity/unreal rows of the gamedev router) and the `blender-animation` row gains mocap-retarget/loops routing and `references/api-changes-5x.md` re-verified against **Blender 5.2.3**; `blender-pipeline-automation` CI recipe tarball `5.2.2` → `5.2.3`; `blender-export-pipelines` and `blender-rendering` only carry the version bump. **`oil-ui`** `e3334bd5` → `56240e1f` (version `0.27.1` → `0.28.0`: evidence policy — stills and `--frames` sequences by default, `--record` only when feel at real speed matters — simplified review handoff, pragmatic verification-script rules; `scripts/shoot.mjs` refactored, `tests/test_shoot.py` hardened with an ffmpeg must-not-run stub). **`rust-review`** `f9296128` → `40db61c6` (new review rules: `impl Into<T>` in application code, `Vec`-return vs iterator on library functions). Root-level-skill pitfall noted: an upstream-compare file filter keyed on `skills/<name>/` misses `oil-ui` (repo-root skill) — it read as a re-pin in pre-checking but is a full content update.
- Re-pins (pin moved, bytes identical, fingerprint-verified by the script): `frontend-design` + `skill-creator` → `a7ba5b93db0c` (anthropics/claude-plugins-official); `moli-webfetch` → `898ba89d` (lexmount/moli); `rust-port` → `40db61c6` (BeautifulRust — sibling of the `rust-review` content change); `rust-best-practices` → `9dda1397` (apollographql/skills).
- Review before update (§5/§6): kit diffs read in full (21 modified files, 0 new, 0 removed, no binaries, no secrets, no machine paths); `oil-ui` script diffs additionally scanned for network/exec patterns (only an SVG XML namespace and the test-side ffmpeg stub). Gate green: 210 tests, ruff 0.16.9, canon v3.2 checks ×2, `skills check .` exit 0 after the dogfood install re-sync (11 applied); exactly 11 `ref` changes in `skills.json`.

## Tooling — 2026-10-29: on-demand skills refresh (3 content updates, 43 re-pins)

- User-triggered cycle (the anonymous-API dry-run had flagged 2+ updates but died on 403; see the 2026-10-22 quota note — recovery identical: pins resolved outside the REST quota via authenticated `gh api`, then `update --skill <name> --ref <sha>` per skill, all fingerprint checks still running). **46 skills moved, 0 refused.**
- Content updates: **`oil-ui`** `c60d91d0` → `e3334bd5` (version `0.26.0` → `0.27.1`: default single design direction with explicit on-demand exploration — new references `task-explore.md`/`task-review.md`; upstream's new `.github/` CI workflows ride along because the skill is vendored from the repository root); **`router`** `184b72be` → `19d93f97` (new `references/custom-engines.md` — custom/proprietary engines stay on their engine, concepts bind to verified project APIs; routing rows for upstream's new `roblox-simulator-economy` skill — **not vendored**, same deliberate-subset situation as the already-referenced unity/unreal/ebitengine/defold rows); **`rust-review`** `c6f56d27` → `f9296128` (Bevy review guidance — ECS aliasing/ordering/`Commands` bugs, prelude exemption — plus `evals/review-bevy-arena/`; its pointer to `bevy.md` in "the `rust-best-practices` skill's references" dangles in this kit: our `rust-best-practices` comes from `apollographql/skills` (chapter references, no `bevy.md`), a cross-upstream reference upstream cannot see — left byte-identical, no hand-edit of vendored content).
- Re-pins (pin moved, bytes identical, fingerprint-verified by the script): 15 `emilkowalski/skills` skills → `a81dbca0`; 23 `godot-*`/`roblox-*` → `19d93f97`; `frontend-design` + `skill-creator` → `f8c5e7a1` (anthropics/claude-plugins-official); `moli-webfetch` → `9939abc2`; `rust-best-practices` → `ff453486` (apollographql); `rust-port` → `f9296128` (BeautifulRust). New upstream skill `remove-animations` (emilkowalski) was evaluated implicitly by the subset rule: not vendored (no onboarding request).
- Review before update (§5/§6): upstream compare ranges read for all 7 moving sources; kit diffs read in full (13 modified files, 22 new files across 5 new paths, no binaries, no secrets, no machine paths). Gate green: 210 tests, ruff 0.16.9, canon v3.2 checks ×2, exactly 46 `ref` changes in `skills.json`; kit dogfood install re-synced (48 applied, the 2 known live-harness orphans untouched per §5).

## Tooling — 2026-10-28: llm-evals skill

- New authored skill: **`llm-evals`** (MIT, doc-only: SKILL.md + 3 reference files, no script, no new write path) — tool-selection guidance and pinned wiring recipes for the three LLM-evaluation frameworks evaluated on 2026-10-28: **Promptfoo** `0.125.1` (default pick: prompt regression and CI gating on local OpenAI-compatible endpoints — llama.cpp `llama-server` via `openai:chat` + `apiBaseUrl`, Ollama via `ollama:chat`; OSS red-teaming runs locally), **DeepEval** `4.3.2` (pytest-style semantic metrics, G-Eval/faithfulness/hallucination; judge-free `system_one` mode; first-class `set-ollama`, per-metric `DeepEvalBaseLLM` for llama.cpp) and **Inspect AI** `0.3.285` (agent evals: Task/solver/scorer, `inspect view`, `local` sandbox without Docker; **Python ≥ 3.11** floor). Every fact was checked against the official docs fetched 2026-10-28; versions, licenses and source URLs are pinned per reference file; unverified points are flagged (promptfoo exit-code doc inconsistency 1-vs-100, DeepEval JUnit absent from 4.x docs, Inspect Docker-on-Windows).
- The frameworks are **never vendored** (they ship no SKILL.md, and the kit stays zero-dependency): they enter a consuming repository as `uv add` / npm dependencies when that repository adopts evals — one tool per repo. **Self-Refine** and **Reflexion** were evaluated and skipped: dormant 2023 research artifacts whose ideas (iterate-with-feedback, verbal reflection after failure) are already carried by the canon's execution loop (§3), agent PR review (§4) and the reality-checker/auditor skills.
- Audit, decision table and fleet candidate repositories (`Prompt-Vault`, `AIFeeder`, `trad-fr-to-en`, `gen-cv`, `rag-ollama`, `postfix-log`, `ocr-to-validation` for promptfoo/DeepEval; `graph-orchestrator-smolagents`, `computer-use`, `oil-agent` for Inspect): `docs/llm-eval-skills-2026-10-28.md`. Adoption stays a per-repo decision (own sprint, own PR); a promptfoo pilot is the natural first wiring.

## Tooling — 2026-10-26: weekly skills refresh (24 content updates, 3 re-pins)

- First automated Monday run (automation-1df38931). **24 content updates — the whole gamedev pack** (`gamedev-skills/awesome-gamedev-agent-skills` `38a4c2500eeb` → `184b72be0288`): upstream's coordinated `refresh/2026-10` pass (115 commits, every version baseline re-checked on 2026-10-24) re-verified the skills against current engine docs — Godot 4.7 typing notes (typed-return overrides, `maxi/maxf`, packed-array setters), one-way collision direction, Jolt joints, TileMapLayer input space, animation track types, deprecated `AudioEffectLimiter`, multiplayer owner-RPC/auth fixes; Roblox datastore load gate, Builder Sans fonts (Gotham removed), remote throttling/Server Authority, Device & Network Simulator. New engines added upstream (ebitengine, defold) are outside the vendored subset.
- Review before update (§5/§6): tarball at `184b72be0288` diffed against the vendored copies — 47 files changed, 0 removed, no binaries, no CRLF, no secrets/machine paths; upstream LICENSE and NOTICE byte-identical to the kit copies (Apache-2.0 attribution unchanged); the only new non-ASCII are the symbols `⟩` and `⚠` (no French diacitic — guard green regardless, vendored-with-source exemption).
- Re-pins (pin moved, bytes identical, fingerprint-verified): `frontend-design` + `skill-creator` → `58267944` (anthropics/claude-plugins-official), `moli-webfetch` → `baf87cfb` (lexmount/moli).
- Quota handling per the 2026-10-22 note: the dry-run died on 403 for the last 6 sources (~78 API calls vs 60/h); `git ls-remote` showed `design-taste` (`c4a6bff0`), `obra/superpowers` (`2ce8aa15`) and `emilkowalski/skills` (`2d228630`) already at HEAD — nothing to do — and only `claude-plugins-official` had moved, recovered via `update --skill <name> --ref <sha>` (no API calls). Zero-refusal fleet deploy follows the merge.

## Common block v3.2 — 2026-10-24

- §4 gains three **GitHub delivery rules** for agent-driven work, complementary to the existing branch/stop/push rules: **PRs stay small and deterministic** (one PR = one self-contained change — declared scope, no drive-by edits, green tests, a diff reviewable in one pass and rebuildable from the branch alone); **agents review the PRs** (an orchestrator agent dispatches review agents over every submitted PR — diff + checklist — and their findings are folded back into the branch before human review); **stacked delivery on long arcs** (long work is cut into a series of small end-to-end PRs, each green and mergeable on its own and stacked on the previous one — never one long-lived branch piling up unreviewed work).
- **What changes for the fleet**: nothing breaks — repositories simply report "behind (v3.1, canon v3.2)" until resynced (`sync_agents.py sync`). The rules bind agent behavior on every future PR, in every fleet repository; no migration, no file to touch besides the block itself.

## Tooling — 2026-10-22: weekly skills refresh

- First run of the weekly update cycle (dry-run → upstream review → re-pin/refresh): **2 content updates + 27 re-pins (content identical), 0 refused**. Content updates, both from `gamedev-skills/awesome-gamedev-agent-skills` (`0a70cfc6` → `38a4c2500eeb`): **`godot-nodes-scenes`** gains a self-contained reference checker (`scripts/check_godot_project.py`, 1262 lines, stdlib-only — argparse/json/os/posixpath/re/struct/sys; no network, no subprocess, no machine paths; read-only validation of `res://` paths, Ext/SubResource ids, `parent=` paths, main scene + autoloads; Python 3.10+) plus the matching SKILL.md rule; **`roblox-luau`** gains a static-checks SKILL.md rule (selene with `std = "roblox"`, luau-lsp analyze over a Rojo sourcemap). Review before update (§5/§6): tarball diffed against the vendored copies, upstream NOTICE verbatim-identical to `docs/upstream-notices/`, Apache-2.0 unchanged, no binaries.
- Re-pins (pin moved, bytes identical, fingerprint-verified by the script): the other 22 `godot-*`/`roblox-*`/`router` to `38a4c2500eeb`; `frontend-design` + `skill-creator` → `af59ee3a` (anthropics/claude-plugins-official); `using-superpowers` → `2ce8aa15` (obra/superpowers); `moli-webfetch` → `644b82c7` (lexmount/moli); `rust-best-practices` → `f9843dce` (apollographql/skills). The blender pack (`71d031da`), video pair (`59744a69`), design-taste (`c4a6bff0`), emilkowalski (`2d228630`) and good-css (`92d436ba`) upstreams did not move.
- Operational note for the next weekly run: one `update` pass needs ~78 anonymous GitHub API calls (one `resolve_ref` per vendored skill) and the anonymous quota is 60/h per IP, so a full pass can die on 403 partway (this run did, after 2 writes). Recovery used here, all inside the tool's contract: resolve upstream HEADs with `git ls-remote` (git protocol, outside the REST quota), then `update --skill <name> --ref <40-hex-sha>` per skill — a full sha is taken as is without any API call, and every fingerprint check still runs. Alternatively wait out the sliding window (~1 h) and rerun `update`.

## Tooling — 2026-10-21: gamedev skills pack (vendored subset)

- New vendored skills (24): **16 `godot-*` + 7 `roblox-*` + `router`** (Apache-2.0, `gamedev-skills/awesome-gamedev-agent-skills` pinned at `0a70cfc6`) — the kit's first game-engine coverage: Godot skills version-pinned to **4.7** (same release as the knowledge-router Godot corpus), Roblox skills for the fleet's `roblox` repository, and the master router (engine detection by project fingerprint, one engine + additive disciplines/genres, progressive disclosure, explicit gap fallback). Text-only (md/json/yaml, zero binaries — no `.gitattributes` change), UTF-8/LF, no French characters, no secrets, no instruction-injection patterns.
- Deliberate subset (24 of the 74 upstream skills), same discipline as the blender pack: only engines the fleet works with; Unity, Unreal, web engines, Bevy/pygame/LÖVE, the 15 cross-engine disciplines and 9 genres stay upstream — natural follow-up if gamedev work grows. The router's catalog covers all 74; for engines not vendored it states the gap by design (§6 of its SKILL.md).
- **Apache-2.0 attribution**: the upstream NOTICE (original works authored from primary docs, engine trademarks descriptive) is preserved verbatim at `docs/upstream-notices/awesome-gamedev-agent-skills-NOTICE`; every skills.json entry records `license: Apache-2.0` + source + pinned ref.
- Decisions on the three sibling candidates (audit in `docs/gamedev-skills-2026-10-21.md`): **yihui-dev/awesome-opus5-5-videos → REFERENCE row** in `docs/video-skills-2026-10-19.md` (703 Opus 5.5 video prompts, no skills — also a Skillry funnel); **LiCinCan/blender-ai-mcp-addon → WATCH** (Blender 4.2+ extension embedding an MCP server over authenticated Streamable HTTP — not a skill, 3 commits, and an endpoint inside the Blender GUI does not fit the fleet's CLI-launched lifecycle model); **MaxLiu22/Motion2MixamoRig → REFERENCE row** (video→Mixamo retargeting tool, ~5 GB ML weights, non-commercial SMPL-X terms — a local tool at most, never vendored).
- Router caveat documented: its `skills/<engine>/...` paths assume the upstream repo layout; kit deployments live flat under `.agents/skills/<name>/` — resolve by name, same treatment as kinetic-reel's hardcoded `~/.claude/skills/` path.

## Tooling — 2026-10-19: video / animation skills onboarding

- New vendored skills: **`kinetic-reel`** and **`painted-animation`** (MIT, `tuzhechen2005/opus-video-skills` pinned at `59744a69`) — the kit's first frame-rendering video skills: kinetic-typography reels (Canvas 2D + three.js WebGL, beat-locked synthesized score) and hand-painted watercolour/ink cartoons (p5.js + p5.brush), both rendered frame by frame in headless Chrome and encoded with ffmpeg. `painted-animation` bundles JohnHeibel/ClaudeAnimationBase as its template with the Heibel MIT license preserved, so ClaudeAnimationBase itself is not vendored.
- New authored skill: **`video-toolchain`** (MIT) — the prerequisite gate every video task runs first: probes node, ffmpeg, python-with-numpy-Pillow (uv env first, §1 rule), Chrome (`--chrome` > `CHROME_PATH` > `PLAYWRIGHT_CHROME` > standard install paths > PATH) and optional ruby; exit 1 with one `fix:` remediation line per missing tool, `--json` for machine use. Stdlib-only, read-only, 23 hermetic tests.
- Decisions (audit + render evidence in `docs/video-skills-2026-10-19.md`): **lemo-opuscar stays a pointer** (136 MB library cloned by its setup into `~/lemo-opuscar` — a home-dir write the agent must disclose; style demos are not turnkey: the paper-popup demo waits for a TTS `voices/dur.json` that is not shipped, the watercolor still needs `paper.py` via numpy+Pillow, `fetch_fonts.mjs` Google Fonts and `PLAYWRIGHT_CHROME`); **motion-graphics-music-video skipped** (Ruby 3.2+ entry layer not installed, paid Fal API behind the `FAL_AI_API_KEY` env var — name-only in docs, macOS-only Swift stage); **shipvideo skipped** (no license, OpenComputer agent app, no code copied). Reference-only list included.
- Rehearsal numbers recorded: kinetic-reel 17 s demo / 510 frames / ~22 s render but **~100 MB default encode — always cut a web copy** (the ffmpeg line is in the doc and the video-toolchain SKILL.md); painted-animation ~390 ms/frame on a non-GPU machine.
- `.gitattributes` gains `-text` overrides for binary extensions: the first vendored skill with jpg/gif assets would have been corrupted by the blanket `skills/** text eol=lf` on the next checkout (lesson [2026-10-19] in AGENTS.md).

## Tooling — 2026-10-18: Blender skills pack (vendored subset)

- New vendored skills: **`blender-core`**, **`blender-export-pipelines`**, **`blender-rendering`**, **`blender-pipeline-automation`** (MIT, `EL4CTEO/blender-skills` pinned at `71d031da`) — first Blender coverage in the kit, aligned with the Blender 5.2 LTS corpus served by the knowledge-router fast path. `blender-core` routes and runs bpy (headless CLI or live MCP), the three others cover verified export presets (Roblox/Unity/Unreal/Godot-web/USD), Cycles/EEVEE batch rendering, and folder-scale batch automation.
- Deliberate subset (4 of the 22 upstream skills): the vendored four are self-contained (each carries its own `_bpyx.py` helper) and match the fleet's 3D pipelines; the upstream router table in `blender-core` and two doc examples in `blender-pipeline-automation` mention sibling skills that are not vendored — read as pointers, not dependencies. Review before `add` (§5/§6): scripts scanned — no network, no eval, one legitimate `blender -b -P` subprocess; upstream ships 50 headless Blender tests of its own.
- `run_in_blender.py` carries the only shebang and is committed 100755 (EXE001 discipline); non-ASCII in the skills is pure typography (→, ·, ≥), no French — the vendored-with-source exemption applies regardless.

## Tooling — 2026-10-18: gpui-kit skill

- New authored skill: **`gpui-kit`** (MIT) — build cross-platform Rust desktop apps with GPUI Kit (Longbridge's component library on Zed's GPUI engine, shadcn/ui-inspired, 75+ components). Covers the minimal bootstrap recipe with exact Windows prerequisites (VS 2022 Build Tools MSVC + Windows SDK, CMake on PATH, MSVC toolchain not GNU), the "rules that bite" (`init(cx)` before any window, never return a second `Root`, never depend on `gpui`/`gpui-pre` directly, two-layer imports, 0.x API churn — pin the tested version), the component map (virtualized data tables, dock layout, charts, markdown, tree-sitter/LSP editor), semantic-token theming, and a "when to prefer Slint/egui/Tauri" guide.
- Live-verified on Windows 11 (2026-10-18): `cargo add gpui-kit@0.7.3` + `cargo check` on the official getting-started snippet — exit 0, 798 locked packages, ~50 s cold. Sources: gpui-kit.com docs for v0.7.3 + `llms-full.txt`, plus the upstream repo's own agent skills (`skills/gpui-kit`, `skills/gpui-kit-design-guides` in longbridge/gpui-kit). Fleet deployment pending explicit GO.

## Tooling — 2026-10-18: MCP fleet management (agent-mcp)

- New kit concern — the machine's **MCP servers** — with the same disciplines as the other three: new stdlib-only CLI `scripts/mcp_agents.py` (Python 3.11+, zero dependency), authored skill `skills/agent-mcp/` (MIT, `NOTICE.md` provenance, byte-identical mirror test-enforced), LF-pinned paths in `.gitattributes`.
- Commands: `inventory` (parses user-level configs holding a `mcpServers` or `mcp.servers` key + repo-level `.mcp.json` files walked under the fleet roots; token-like values masked), `audit` (declared vs running: localhost HTTP / process / command probes, `up / down / unknown`), `probe <name>` (probe + freshness globs like `**/BUILT_AT.txt` with an age budget + every absolute path referenced by the server's own config file), `doctor` (all of it, exit 1 on any down/stale/missing — CI gate), `start|stop|restart <name>` (runs the lifecycle commands declared in the descriptor; the only effectful commands).
- **Fleet descriptor**: machine specifics live in a local, git-ignored `mcp-fleet.local.yml` next to `.agent/` (template committed as `template/mcp-fleet.template.yml`, path-free, guard-tested). The kit keeps carrying no machine path and no server name. Discovery order: `--config` > `MCP_FLEET_CONFIG` > `<repo>/mcp-fleet.local.yml` > upward walk.
- **Safety**: the read-only commands never write; token/key/secret/password values are masked in every output including `--json`; lifecycle actions run only what the descriptor declares. `.gitattributes` gains `template/** text eol=lf` (byte-stable templates across checkouts) and `skills.json text eol=lf`.
- Real verification (2026-10-18): `doctor` caught a search daemon down for 8 days (exit 1) plus 3 directories referenced by its config that no longer exist; the declared `start` command brought it back (HTTP 200), and the second MCP entry (stdio fast path) reported HEALTHY with fresh corpus markers. Rollout and redacted evidence: `docs/mcp-fleet-rollout-2026-10-18.md`.

## Common block v3.1 — 2026-10-18

- §2 policy flip: the ledger database is **local-only** — `.agent/` (state database, legacy backups) and `.agents/` (installed skill copies) are git-ignored from initialization and never committed (a heavy binary and installed scripts would bloat public GitHub repositories and skew their language statistics). The on-disk state remains the source of truth; only its git carriage changes.
- **Fleet migration (one-time per repository)**: if `.agent/` or `.agents/` were committed before, untrack them without touching the disk — `git rm -r --cached .agent .agents`, commit, push. `sync_agents.py init` and `skills_agents.py sync` now pin both entries in the target `.gitignore` automatically (runbook in `docs/MIGRATION.md`).

## Tooling — 2026-10-18: per-repo skill opt-out

- `skills sync`/`check`/`deploy`/`audit` respect a per-repository opt-out file, `<repo>/.agents/skills/.agents-kit-ignore` (one skill name per line, `#` comments — same idiom as the fleet-root repository exclusions): an opted-out skill is never installed and an installed copy is pruned as an orphan (no `--force` needed, no refusal for an unmanaged copy). An explicit `--skill <name>` bypasses the opt-out. Motivation: curate relevance (the 15 design/animation skills from emilkowalski are useless in backend/infra repositories) without forking the registry.

## Tooling — 2026-10-18: local-only .gitignore enforcement

- `sync_agents.py init` writes or extends the target `.gitignore` with `.agent/` + `.agents/` (idempotent, existing content preserved, refusal paths write nothing).
- `skills_agents.py sync` (and `deploy`) pin the same entries in every repository it touches, with an untrack reminder printed when it adds them; `--dry-run` never writes.
- `state_agents.py` unchanged (its `.agent/*.duckdb.wal` line stays valid, now subsumed by `.agent/`).

## Common block v3.0 — 2026-10-16

- §2/§3 rewritten: the 4-file markdown/JSON ledger (`feature_list*.json`, `contract.md`, `progress.md`, `log.md` + monthly rotation into `docs/journal/`) is replaced by **one DuckDB database, `.agent/state.duckdb`**, managed exclusively through the new `agent-state` skill CLI. Variant B is absorbed: the database IS the standard.
- The **4 operational directives** are kept and tightened: bounded `bootstrap` (active features, sprint, contract, last 20 log entries — never query the full history unfiltered, `search-log` instead), `log` at the start and end of each action, immediate `feature`/`step`/`contract` sync, `bootstrap` again as crash recovery (last committed transaction = valid state).
- A legacy 4-file ledger is auto-migrated **with backup** on the first `bootstrap` (`.agent/legacy_markdown_backup/`); the 7 historical log types (`init gen eval fix sync done err`) migrate losslessly.
- `sync_agents.py init --ledger` now prepares `.agent/` (no legacy files written); `ledger` reports the database when present, legacy checks otherwise. `--variant-b` stays recognized for not-yet-migrated repositories.
- Block size: 7 994 → 7 122 bytes (budget < 8 KB).
- **Migration (order matters)**: DEPLOY THE SKILL FIRST — `skills_agents.py sync <repo>` (installs `agent-state`), THEN `sync_agents.py sync <repo>` (canon v3.0), then run `state_agents.py migrate --repo <repo> --backup` (or let the first `bootstrap` do it). A repository left on v2.3 after kit `main` moves reports "behind" in the weekly CI until synced — release the kit and roll the fleet in the same window (runbook in `docs/MIGRATION.md`).

## Tooling — 2026-10-16: agent-state skill (DuckDB ledger CLI)

- New authored skill **`agent-state`** (MIT) shipping `scripts/state_agents.py` (byte-identical mirror, test-enforced): PEP 723 header declares `duckdb>=1.1.0` — `uv run --no-project <script> <command>` builds and caches an isolated environment, no global install, works on fresh clones and CI. Empirically verified against duckdb 1.5.6 (scratch probe; duckdb.org pages are client-rendered shells — facts proven by execution per §6).
- Schema (idempotent, sequences for integer PKs): `features` (status CHECK, `dependencies VARCHAR[]`), `contract_meta` (`test_command`), `contract_criteria` (passed/locked), `sprint_progress` (objective/milestone), `execution_log` (7-type action CHECK, append-only). Ephemeral connections only (`.wal` folds into the database on clean close — verified).
- `migrate [--backup]`: ONE transaction (rollback leaves the repository where it started, database removed if it was just created); parses both English and legacy French formats (headings, test-command line); tolerates bare-list archives; coerces unknown statuses to `pending` with a warning; re-keys archived ids colliding with reused active ids to `AA-<id>` (the kit's own ledger reuses F-xx across sprints — found by the rehearsal on real data, no silent loss); counts skipped `## [` lines; `--backup` archives sources and pins `.agent/*.duckdb.wal` in `.gitignore`.
- Commands: `bootstrap` (auto-migration when the database is absent), `log`, `feature add/status`, `step add/done/reset`, `contract add/pass/cmd`, `search-log` (ILIKE, `--limit`), `export-md` (`.agent/DASHBOARD.md`). 19 new tests (118 total) — the suite now runs with `--with "duckdb>=1.1.0"`; English-only guard gains `.agent` in its SKIP set (binary database + migrated backups are state, not authored content).

## Common block v2.3 — 2026-10-11

- §1 **Code search**: on large repositories (> 5k files, or a `.tgrep/` index folder present), agents must prefer the fast indexed `tgrep` CLI over slow recursive scans (`grep -r`, `find`, `Select-String`) — the pain point of big-asset projects (e.g. game repositories): `tgrep -- "pattern" .`, `tgrep -t <type> -- "pattern" .` for one file type (first use: `tgrep index .`; keep `.tgrep/` git-ignored). Below ~2k files, plain `git grep` and the standard tools are already instant. The block names the tool and the usage only; it stays free of machine paths (genericity invariant) — the binary (microsoft/tgrep, Rust, MIT) is installed on the fleet machines in `~/.local/bin`, already on PATH.
- Adopted on measured evidence, per §6: binary `tgrep 0.1.6` verified live (`--help` surface, index built in `.tgrep/`, query answered in 0.5 ms on an indexed corpus, `count-files` walker); upstream README pinned at fetch time (commit `669e832b`): client/server design — `tgrep serve . [--exclude <dir>]…` auto-builds the index in the background and clients connect automatically.
- Template §7 "Key commands" gains the big-project example: `tgrep serve . --exclude .godot`.
- Block size: 7 648 → 7 994 bytes (budget < 8 KB). **Migration**: v2.2 repositories are "behind" → `sync <repo>` (fleet sync after this kit release is merged); §7 untouched.

## Tooling — 2026-10-04: agy skill

- New authored skill: **`agy`** (MIT) — drive Google Antigravity's `agy` CLI headless, image generation first: the verified recipe (disposable cwd + `--dangerously-skip-permissions`), the three-point success check (status + `denied_actions`, magic bytes on disk, image actually looked at — a soft-denied run still exits 0 with status SUCCESS), salvage of generated images from `~/.gemini/antigravity-cli/brain/<conversation_id>/` after a denied copy, reference-based iteration via `--continue` / `--conversation`, and machine-readable output handling (text / json / stream-json, parsed with Python — `jq` not assumed). Every rule measured live on agy 1.2.16 (2026-10-04), including the doc-vs-binary drift (`--print-timeout` default, `--effort xhigh|max`, undocumented `denied_actions`) and the workspace-context leak (the enclosing repo's AGENTS.md and `.agents/skills/` shape the run). Official reference pinned at fetch time: https://antigravity.google/docs/cli/headless/

## Tooling — 2026-10-04: project-dashboard skill

- New authored skill: **`project-dashboard`** (MIT) — build a visual dashboard of a project's real state as a single-file interactive HTML page in the reader's chat language: features by status, contract criteria with validation evidence, tests/CI, git position, debts and lessons. Every number is measured from the repository itself (ledger files, git, command outputs) with its source cited; stale or unverifiable data is labeled, never smoothed. Quality bar shared with `explainer`: deliberate design, screenshot inspected before delivery. Read-only on the repository; the artifact is disposable under `scratch/`.
- Guard carve-out: `scratch/` (disposable chat-language artifacts, git-ignored) joins the English-only test `SKIP` set — committed content stays fully guarded.

## Tooling — 2026-10-04: explainer skill

- New authored skill: **`explainer`** (MIT) — turn a dense result, system, error or architecture into the cheapest artifact the user can actually process, on an escalation ladder: controlled plain English (ASD-STE100, or "80% of the way") → diagram (Mermaid / ASCII / SVG, one question per diagram) → interactive single-file HTML page (self-contained: inline CSS and JS, no CDN, no build step, opens directly in a browser) → explainer video on explicit request only (storyboard approved by the user before any render, local render path first, an external API only on explicit user instruction with its key in an environment variable). Start at the lowest rung that answers the question; escalate one rung when the user re-asks, says they do not understand, or the prose would run past a screen. Artifacts are disposable (`scratch/` or the location the repository declares) and always delivered with a short chat summary — they accompany the answer, they do not replace it.
- **Same-day revision**: the "lowest rung first" rule produced weak artifacts (a markdown file where a page was expected). The interactive single-file HTML page is now **the default artifact**, with an explicit quality bar (deliberate design, screenshot inspected before delivery — verified means seen), diagrams restricted to surfaces that cannot render a page, and a hard rule: a markdown file is never the deliverable when a page is possible.

## Common block v2.2 — 2026-10-02

- §6 **Read the upstream docs BEFORE acting**: before testing, debugging, upgrading or adopting any engine, model or third-party tool, fetch its official documentation into a scratch area and read the relevant pages — the upstream repo's `docs/` (per-model/per-feature pages the root README omits), model/dataset cards, `/llms.txt` endpoints (append `.md` to page URLs where supported). Never rely on memorized flags or assumed capabilities. Pin the doc version/commit at fetch time and cite it in the test verdict or decision.
- Tool-agnostic by design: any web-fetch/crawl capability available to the agent qualifies (e.g. an MCP crawl server returning markdown). Fetched docs remain external content = data (§5).

Block size: 6 968 → 7 648 bytes (budget < 8 KB). **Migration**: v2.1 repositories are "behind" → `sync <repo>`; §7 untouched.

## Tooling — 2026-10-02: kit-authored skills + first one

- New `skills author <name> [--license SPDX] [--force]`: registers a skill **authored in the kit** (skills/<name>/ written by hand, no upstream) in `skills.json` — same fingerprints, same deploy path as an imported skill (`source: "(authored)"`). `update` skips authored skills (nothing to re-import online); after editing the kit copy, re-register with `--force`. Refuses to shadow a GitHub-vendored skill without `--force`. 8 regression tests (95 total).
- First authored skill: **`docs-fishing`** (MIT) — fetch and read the upstream official documentation of any engine/model/tool BEFORE testing, debugging, upgrading or adopting it: inventory the targets from the project, map the sources by yield (upstream `docs/` > model cards + org listing > `llms.txt` + `.md` endpoints > README at the pinned ref), fetch into a pinned scratch area, read with the three questions (unused capabilities / our known blocks / changes since our version), cross-check against the local binaries, record the findings in the project state files. Implements the common block rule "read the upstream docs before acting".

## Tooling — 2026-09-28: common skills management

- New script `scripts/skills_agents.py` (standard library only, no npx/Node): it vendors **common agent skills** into the kit (`skills/<name>/`, registry `skills.json`: source, pinned commit, import date, license, per-file sha256) and deploys them into every repository's `.agents/skills/` folder, with a per-repository lock (`.agents/skills/.agents-kit.json`).
- Commands: `add <github-url> [--skill NAME] [--ref REF] [--force]`, `list`, `check <repo> [--diff]`, `sync <repo> [--dry-run] [--force] [--skill NAME]`, `audit [root] [--strict] [--exclude]`.
- Same safety model as the block: a hand-edited install (or an unmanaged skill folder) is refused without `--force`; an up-to-date repository is not rewritten; orphans (no longer vendored) are pruned; `check`/`sync`/`audit` need no network — the kit copy is the single distribution source, so an imported skill is reviewed once and pinned by commit.
- **Update cycle**: `skills update` (online) re-imports the vendored skills whose upstream moved on (registry refreshed: ref, files, license, `updated` date; hand-edited kit copies refused without `--force`; identical content on a new commit only re-pins); `skills deploy [root]` (local) then propagates to every repository that already has `.agents/skills`, with per-repository refusals that never block the rest of the fleet (`--dry-run`, `--strict`, `--skill`, exclusions). Repositories without `.agents/skills` are never touched.
- First vendored skill: `using-superpowers` (obra/superpowers, MIT, pinned commit `8ca22db`), deployed across the fleet (13 repositories pushed, see the kit log).
- **The common block is unchanged**: no `sync` needed on the fleet for this entry. To deploy the skill: `skills sync <repo>` in each repository (or `skills audit` to see who has what).

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
