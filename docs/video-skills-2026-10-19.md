# Video / animation skills onboarding audit — 2026-10-19

Evaluation of the third-party video/animation skill repositories considered for the
kit, the vendor / pointer / skip decision taken for each, the SKILL.md risk audit
(§5 discipline: external content reviewed as data before `skills add`), and the
prerequisite gate shipped with them. Live render evidence comes from the
2026-10-19 rehearsal session on Windows 11 (node, ffmpeg, python, Chrome present).

## Decision table

| Repository | Decision | Reason | Pinned SHA | License |
|---|---|---|---|---|
| tuzhechen2005/opus-video-skills — `kinetic-reel` | **VENDOR** | Works out of the box (17 s demo, 510 frames, ~22 s render), self-contained template, MIT | `59744a69c7b916cfbe4c4ec84006b0c2f5e2fde1` | MIT |
| tuzhechen2005/opus-video-skills — `painted-animation` | **VENDOR** | Works (11 s clip at ~390 ms/frame), bundles ClaudeAnimationBase as its template, MIT | `59744a69c7b916cfbe4c4ec84006b0c2f5e2fde1` | MIT (template portion: MIT, John Heibel, `template/LICENSE`) |
| lemomo-ai/lemo-opuscar | **POINTER** (never vendored) | 136 MB repo; skill clones the library into `~/lemo-opuscar` (home-dir write); style demos are not turnkey (see below) | `b5e8ef93930b6d828f352055a689320f138237b1` | MIT |
| JohnHeibel/ClaudeAnimationBase | **SKIP** (absorbed) | Already bundled as `painted-animation/template/` with its MIT license kept; nothing left to vendor | `0ac8bf2b31942376cb6b8c4074715595d512acd2` | MIT |
| makevoid/motion-graphics-music-video-skill | **SKIP** (reference) | Ruby 3.2+ only entry layer (not installed on the fleet machine), paid Fal API behind `FAL_AI_API_KEY`, Swift VFX stage needs macOS 14+ | `75aafbe3a986cda3a56ce4d046da0d558fc10983` | MIT |
| diggerhq/shipvideo | **SKIP** (reference) | No license — no code may be copied; requires an OpenComputer agent, not a skill | `53d7c6f752fb85b449de8cf806b77ad21808a8f1` | none |

Reference-only (prompts and inspiration, never code): JohnHeibel/PDoomVideo (no
license), the awesome-opus5-5-videos lists (yihui-dev, athemeroy, BeatAPI),
tidewater, claude-opus-5-5-demo (no license).

## SKILL.md audit (frontmatter, triggers, instruction risks)

### kinetic-reel (vendored)

- Frontmatter: `name` + a long trigger-rich `description` (reel, showreel,
  motion-graphics / kinetic-type video, "Work Reel"). No extra fields, no
  license field — license read from the repo root (MIT).
- Writes: the scaffold (`scripts/new_project.sh`) copies `template/` into the
  **target project directory**, creates `out/` and `assets/` there, and runs
  `npm install` in the target (network fetch of puppeteer-core + three, written
  into the target's `node_modules/`). No write outside the project, no
  `curl | sh`, no npm install lifecycle scripts in the template `package.json`.
- The SKILL.md text hardcodes the Claude Code skill base path
  (`~/.claude/skills/kinetic-reel/...`). Kit deployments live under
  `.agents/skills/kinetic-reel/` — resolve the base directory of the loaded
  skill instead of copying that literal. The vendored copy stays byte-identical
  (fingerprints refuse local edits).
- Rendering: `render.mjs` drives **headless Chrome** (auto-detected; `--chrome`
  or `CHROME_PATH` override) frame by frame; ffmpeg encodes. The score is
  synthesized locally (`music/score.mjs`) — no network audio service.
- Rehearsal measurements (2026-10-19): 17 s demo, 510 frames, ~22 s total
  render. **The default encode is ~100 MB for 17 s** — always produce a web
  copy after encoding (`ffmpeg -i out/reel.mp4 -vf scale=1600:900:flags=lanczos
  -c:v libx264 -preset slow -crf 23 -c:a aac -b:a 128k -movflags +faststart
  out/reel-web.mp4`).

### painted-animation (vendored)

- Frontmatter: `name` + trigger-rich `description` (animation, cartoon, music
  video, lyric video, animated GIF/loop, "a video of Clawd"). Clean.
- Writes: same scaffold pattern as kinetic-reel (template copy + `npm install`
  p5, p5.brush, puppeteer-core **into the target project**). Nothing outside
  the project; no lifecycle scripts.
- Provenance: distilled from JohnHeibel/PDoomVideo via ClaudeAnimationBase,
  which is bundled as `template/` with its own MIT license file — both
  preserved byte-identical in the vendored copy (26 + 29 tracked files; the
  upstream `node_modules/` and `out/` are gitignored there and absent here).
- The engine rules (pure functions of `t`, `boilSeed`, no p5-name collisions)
  live in the bundled `ANIMATION_GUIDE.md` — the skill instructs reading it in
  full before designing; it is content, not instructions to the agent host.
- Rehearsal: 11 s clip at ~390 ms/frame on a non-GPU machine — budget minutes,
  not seconds, and prefer `--sheet` review passes over full renders.

### lemo-opuscar (pointer — prerequisites recorded)

MIT, 51 styles, Claude-plugin layout (`plugin/skills/lemo-opuscar/SKILL.md`).
The skill is a thin **director** that fetches the library and hands control to
its own `AGENTS.md` (external instructions: treat as data, §5 — follow only
after the user approved the workflow). Real prerequisites measured on
2026-10-19, none of them turnkey:

1. `scripts/setup.sh` **clones or updates the library into `~/lemo-opuscar`**
   (a write OUTSIDE any project — run it only with the user informed) and
   prints `LIB=<path>`. `setup.sh deps` installs the core tools (network,
   minutes); `deps voice` / `deps music` are extra.
2. The **paper-popup style demo hangs**: it expects `voices/dur.json`, the
   output of a TTS pass that is not shipped. Produce the voice track (or stub
   the durations file) before any timed render of that style.
3. The **watercolor style** needs `python paper.py` (numpy + Pillow — run via
   `uv run --with numpy --with pillow python paper.py`, §1 uv-only rule) to
   generate `paper.jpg`, then `node fetch_fonts.mjs` (downloads Google Fonts),
   and `PLAYWRIGHT_CHROME` pointing at the Chrome executable; `node render.mjs
   stills 5 20 40` then produced a good-quality still.
4. Windows: clone shallow into a SHORT path (`git -c core.longpaths=true clone
   --depth 1`) — deep paths break the Node dependency resolution. Never vendor
   the repository (136 MB).

### motion-graphics-music-video (skipped, kept as reference)

- Frontmatter declares its own contract: Ruby 3.2+, Bundler, FFmpeg,
  ImageMagick, Python 3, Node 22+, Chrome, macOS 14+ / Swift 5.9+ for the VFX
  stage, and the **paid** Fal queue behind the `FAL_AI_API_KEY` env var (the
  plugin's MCP server holds the key; the CLI reads only the env var). The key
  name may appear in kit docs; no key ever enters the repository (§5).
- "Ruby is the only execution entry layer" — with no Ruby on the fleet machine
  and a paid API dependency, nothing can be verified here; vendoring would ship
  an unverifiable skill. MIT keeps the door open if that changes.

### shipvideo (skipped)

An OpenComputer agent application (`oc-template.toml`, `opencomputer/`,
`web/`), not a skill: no SKILL.md at the root, and **no license file** — code
must not be copied into the kit (§5/§6: unlicensed external content is
read-only reference). Kept as a pointer only.

## Prerequisite gate (video-toolchain skill)

Authored skill `video-toolchain` (MIT), registered in `skills.json`, dogfood
installed in the kit:

```bash
uv run --no-project .agents/skills/video-toolchain/scripts/video_toolchain.py [--json]
```

Probes node, ffmpeg, python-with-numpy-Pillow (uv env first, kit §1 rule),
Chrome (`--chrome` > `CHROME_PATH` > `PLAYWRIGHT_CHROME` > standard install
paths > PATH) and optional ruby; exit 1 with one `fix:` remediation line per
missing required tool. Verified live 2026-10-19: exit 0 (node v24.20.0,
ffmpeg 9.0.2, numpy/Pillow via uv, Chrome at the standard Windows path, ruby
absent and tolerated).

## Fleet notes

- Both vendored skills deploy with the standard
  `skills_agents.py sync <repo>` cycle; nothing to change in consumers beyond
  an optional `.agents-kit-ignore` opt-out for repositories where video work
  is out of scope.
- The MCP fleet is untouched: none of these repos ships an MCP server the kit
  should declare (motion-graphics' plugin MCP is tied to its paid key and stays
  out; `mcp-fleet.local.yml` unchanged).
