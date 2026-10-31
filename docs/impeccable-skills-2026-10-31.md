# Impeccable onboarding audit — 2026-10-31

**Decision**: vendor the `impeccable` skill from `pbakaus/impeccable` (Apache-2.0, pinned
`b7a89176e4e87422b40f98adabceb051dbb5448b`, skill version `0.1.18`, SKILL metadata `4.8.0`).
Upstream: ~97.6k stars, very active (same-day pushes). 63 files / 2.3 MB vendored from the
`.agents/skills/impeccable/` folder of the repository.

## What impeccable is

A design toolkit for coding agents: 24 commands (`critique`, `audit`, `polish`, `bolder`,
`quieter`, `animate`, `live`…), a craft floor of absolute bans, four visitor modes
(Persuade/Operate/Read/Experience), PRODUCT.md/DESIGN.md context capture, four sub-agent
definitions (`agents/*.toml`: asset producer, documenter, finish reviewer, manual edit
applier), and a **deterministic slop detector** (62 rules, no LLM, no API key) runnable
standalone (`npx impeccable detect`, `--github` for Actions annotations) or as an agent hook.
The engine is a Rust binary; the skill embeds only launchers (`scripts/impeccable` sh +
`impeccable.cmd` Windows) and a checksum manifest.

## Review before vendoring (§5/§6)

- Launcher `scripts/impeccable` (263 lines) and `impeccable.cmd` (306 lines) read in full:
  download **only** from `https://github.com/pbakaus/impeccable/releases`, **fail-closed**
  (refuses any download without a matching sha256 in the vendored `engine-checksums.txt`),
  never pipes network content into a shell, probe handshake against stale binaries, egress-free
  sandboxes supported via `IMPECCABLE_BIN` / PATH preinstall.
- Grep sweeps over all 63 files: no `child_process`/`execSync`/`eval` in the JS (browser-side
  DOM tooling), no curl/wget/base64/exfiltration patterns in the markdown, no secrets, no
  machine paths. "Token" hits are design tokens; "http" hits are doc links.
- Behavior-driving playbooks read (`craft-floor.md`, `routing.md`, `new-work.md` head,
  `hooks.md` structure, sub-agent TOMLs): pure design guidance.
- Upstream `NOTICE.md` kept verbatim at `docs/upstream-notices/impeccable-NOTICE.md`
  (ios.md/android.md derive from ehmo/platform-design-skills, MIT).

## The mirror pitfall — and the `--folder` flag

The repository ships the **same skill in two layout mirrors**: `.agent/skills/impeccable/`
(58 files, light variant, prose paths hardcoded to `.agent/skills/…`, slash-command style,
no sub-agents) and `.agents/skills/impeccable/` (63 files, full variant with `agents/*.toml`,
prose paths hardcoded to `.agents/skills/…`). Tar member order made `extract_skill` pick the
light one silently — whose hardcoded paths would be **wrong** in our installs (kit installs
live at `.agents/skills/`).

Fix (generic, not impeccable-specific): `skills add` gains `--folder PATH` — validated
against the candidate folders, recorded in `skills.json` (`folder` key), and honored by
`update` on every future re-import, so the weekly refresh keeps pulling the right mirror.
5 regression tests in `tests/test_skills_agents.py` (`FolderSelection`).

## Weight and churn

2.3 MB / 63 files: `scripts/data/font-index.json` 1.1 MB (typeset command font knowledge),
`scripts/live-browser.js` 550 KB (live variant mode), ~40 reference playbooks, the rest
small. Fleet-wide ≈ 200 MB across ~88 repositories; per-repo opt-out available
(`.agents/skills/.agents-kit-ignore`). Upstream moves fast (0.1.x daily) — the weekly
refresh cycle carries it like the gamedev pack.

## Supply-chain stance

The engine binary is **not vendored** and not fetched at vendor/deploy time: the launcher
downloads it on first run from the project's GitHub releases, pinned to the vendored
`VERSION` and verified against the vendored `engine-checksums.txt` (fail-closed). This
matches the llm-evals discipline: the runtime dependency stays external; the kit vendors
guidance + launchers only. Consuming repositories that forbid egress can preinstall the
engine on PATH or set `IMPECCABLE_BIN`.

## Line endings

`impeccable.cmd` ships CRLF upstream. Kit `.gitattributes` now carries `*.cmd -text` +
`*.bat -text` (byte-exact, no conversion): converting to LF would break cmd.exe `goto`
labels and drift the byte-strict fingerprints on every fresh clone (same mechanism as the
2026-10-18 lesson). **Fleet requirement**: at deploy time, every consuming repository needs
the same `*.cmd -text` line in its own `.gitattributes`, else a fresh clone of that repo
flags the install as hand-edited.

## Not vendored (deliberate)

The repository's other deliverables — npm CLI distribution, VSCode extension, Cursor
plugin, `demos/`, the Rust workspace itself — are distribution channels and engine sources,
not agent skills. The npm CLI stays an external dependency for repositories that want
`impeccable detect` in CI (`npx impeccable detect --github src/`), exactly like the
llm-evals frameworks.

## Routing guidance for the fleet

`impeccable` owns the design **workflow** (commands, modes, craft floor, PRODUCT/DESIGN.md
capture, detector). The existing taste cluster (`design-taste` + genre packs,
`frontend-design`, `apple-design`, `emil-design-eng`, `good-css`, `oil-ui`, `taste-*`)
stays the **aesthetics reference** material impeccable's briefs can pin. UI repos get both;
non-UI repositories can opt out.

## Fleet deploy checklist (post-merge)

1. `skills deploy` as usual (or per-repo `sync`).
2. Add `*.cmd -text` (and `.agents/skills/**/*.cmd -text` if their attributes are scoped)
   to each consuming repository's `.gitattributes` — same one-line fix as 2026-10-16/10-18.
3. First `impeccable` use in a repo downloads the engine (~network + `~/.impeccable` cache);
   CI runners wanting the detector should preinstall or allow the download.
