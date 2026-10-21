# Gamedev agent skills onboarding audit — 2026-10-21

Evaluation of the four repositories surfaced on 2026-10-21, the vendor / pointer /
watch / skip decision taken for each, and the SKILL.md risk audit of the vendored
subset (§5 discipline: external content reviewed as data before `skills add`).

## Decision table

| Repository | Decision | Reason | Pinned SHA | License |
|---|---|---|---|---|
| gamedev-skills/awesome-gamedev-agent-skills — `godot-*` (16) + `roblox-*` (7) + `router` | **VENDOR (subset, 24 skills)** | Real SKILL.md skills, each version-pinned to an engine release ("Targets Godot 4.7" — same release as the kit's knowledge-router Godot corpus; Roblox for the fleet's roblox repository); text-only, no binaries; 2.5k stars | `0a70cfc64672d512c5b5b6006b5dcb5cf90dbdbd` | Apache-2.0 (NOTICE preserved verbatim at `docs/upstream-notices/awesome-gamedev-agent-skills-NOTICE`) |
| yihui-dev/awesome-opus5-5-videos | **REFERENCE only** (row in `docs/video-skills-2026-10-19.md`) | 703 Opus 5.5 video prompts as markdown + JSON, no skills, no code; repository is also a Skillry funnel (every link carries UTM parameters); 10 commits, bulk updates | `92aee2f586ac0715cb3cbcb6384834f98a33383d` | MIT (prompts "belong to their creators" per Credits) |
| LiCinCan/blender-ai-mcp-addon | **WATCH (no action)** | Not a skill: Blender 4.2+ extension (zip) embedding an MCP server with authenticated Streamable HTTP transport; 974 stars but 3 commits / 31 open issues / v1.0.0 — too early; an endpoint living inside the Blender GUI does not fit the MCP fleet lifecycle (CLI-launched servers) yet; kit blender-* skills already cover static bpy scripting | `HEAD 2026-10-20` (not vendored) | MIT |
| MaxLiu22/Motion2MixamoRig | **SKIP / REFERENCE row** | Video → Mixamo-rigged character retargeting tool, no SKILL.md; ~5 GB of ML weights auto-downloaded on first run; SMPL-X model needs manual registration under non-commercial terms (redhibitory for a public MIT kit); Mixamo FBX fetched manually; legacy `chumpy` dependency; CPU 8–15 min per 30 s clip; tested primarily on Apple Silicon (fleet machine is Windows) | `2835dcdfba30e78a2610360b9b2a1e1121d85159` | Apache-2.0 (code); downloaded assets under separate terms |

## Why this subset (24 of 74)

The upstream catalog holds 74 skills: 16 Godot, 8 Unity, 6 Unreal, 6 web engines
(Phaser/PixiJS/three.js), 10 other engines (Bevy, pygame-ce, LÖVE, 7 Roblox),
15 cross-engine disciplines, 9 genres, 4 workflows, plus the router. The kit
vendors what the fleet works with today, same discipline as the blender pack
(4 skills of a larger catalog):

- **Godot 16** — matches the kit's knowledge-router Godot 4.7 corpus exactly.
- **Roblox 7** — the fleet's `roblox` repository already receives the blender
  pack; the knowledge-router also ships a Roblox corpus.
- **router** — engine detection by project fingerprint (one engine, additive
  disciplines/genres/workflows), progressive disclosure, explicit gap fallback.
- Left out by scope: Unity, Unreal, web engines, Bevy/pygame/LÖVE (no fleet
  consumer today), the 15 disciplines and 9 genres (natural follow-up if gamedev
  work grows — the router composes them by name when present).

## SKILL.md audit (subset reviewed at `0a70cfc6`)

- **Shape**: 24 folders, 57 files, 297 987 bytes; extensions md / json / yaml
  only — zero binaries, so the 2026-10-19 `.gitattributes` binary overrides do
  not apply and `skills/** text eol=lf` covers everything.
- **Encoding**: UTF-8, LF only (no CRLF anywhere); non-ASCII is typography only
  (em dash, arrows `→`/`↔`, `≈`, `Ö` in LÖVE, curly quotes, box-drawing); no
  French diacritic — the English-only guard is satisfied outright, and vendored
  skills are exempt anyway (skills.json records the upstream source).
- **Frontmatter**: `name` + trigger-rich `description`, no extra fields; engine
  versions pinned in the body (e.g. godot-gdscript targets Godot 4.7 /
  GDScript 2.0). Companion files are `references/*.md` (depth on demand),
  `agents/openai.yaml` (display metadata only) and two Rojo JSON assets in
  roblox-ui.
- **Content quality**: patterns-first recipes with engine-correct API usage
  (spot-checked godot-gdscript, roblox-luau in full; both teach
  server-authoritative, static-typed, lifecycle-correct code).
- **No secrets, no machine paths**; the grep hits on "secret"/"key" are
  security guidance (never store secrets in `export_presets.cfg`, `.tres`,
  client code, or client-visible remotes).
- **Instruction risk**: none found — no self-referential agent instructions, no
  network fetch-and-execute, no destructive commands.
- **Router caveat**: its paths (`skills/godot/...`,
  `../docs/VERSION-SUPPORT.md`) assume the upstream repository layout; kit
  deployments live flat under `.agents/skills/<name>/`. Resolve skills by name
  instead of copying the literal path — same documented caveat as kinetic-reel's
  hardcoded `~/.claude/skills/` path (vendored copy stays byte-identical). The
  router's §6 fallback ("state the gap, never fabricate") covers the engines the
  kit does not vendor.
- **Provenance**: the upstream NOTICE states every skill is an original work
  authored from primary documentation, with no text or code copied from other
  collections; engine names are used descriptively (trademark notice). The
  NOTICE is preserved verbatim at
  `docs/upstream-notices/awesome-gamedev-agent-skills-NOTICE` (Apache-2.0
  §4 attribution), and every skills.json entry records
  `license: Apache-2.0` + source + pinned ref.

## Fleet notes

- Deploys with the standard `skills_agents.py sync <repo>` cycle; natural
  targets are the `roblox` repository and any gamedev repository (Godot work);
  nothing changes for consumers that opt out via `.agents-kit-ignore`.
- The router catalogs engines the kit does not vendor (Unity, Unreal, web,
  Bevy/pygame/LÖVE): by design it states the gap instead of failing.
- The MCP fleet is untouched: blender-ai-mcp-addon stays a WATCH entry (see
  decision table) until it stabilizes and the fleet model supports an
  HTTP endpoint hosted inside Blender.
