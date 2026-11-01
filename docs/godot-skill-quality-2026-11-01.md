# godot-skill-quality onboarding audit — 2026-11-01

**Decision**: vendor the four Godot 4 visual-quality skills authored by the fleet owner in
`laurentvv/godot-skill-quality` (MIT, pinned `1771e83e3d5a63b4f7ee7320ec8de891d1a36b9b`,
main pushed 2026-11-01). 35 files / ~190 KB total. Local authoring copy verified
byte-identical to the GitHub head (same sha, clean worktree) before review.

## What the pack is

Agent skills (SKILL.md) that make Godot 4 3D scenes look good — every technique measured
in Godot 4.7 against the kit's knowledge-router corpus:

| Skill | Files | Scope |
|---|---|---|
| `godot-lighting-environment` | 9 | Sun, sky ambient, AgX, SSAO/SSIL, SDFGI, fog — applied in order; eval scene + preset script |
| `godot-lights-camera-post` | 7 | Cull-masked fill light, local warm lights, FOV/DoF framing, MSAA/TAA, vignette + grain + dust (`.gdshader`) |
| `godot-render-performance` | 7 | Leave-one-out GPU measurement at a fixed view, then lower the expensive feature's sub-settings (shadow budget script) |
| `godot-vegetation-shaders` | 12 | Leaf-card canopy normals, vertex-colour wind sway, blended ground, MultiMesh grass; 3 `.gdshader` + Blender prep scripts |

Each skill ships LICENSE (MIT), PROVENANCE.md, `references/evidence.md` (measured
results), ready-to-run scripts and `evals/` JSON authored with skill-creator.

## Review before vendoring (§5/§6)

- Complementary to the 16 gamedev-pack `godot-*` skills (scripting/physics/ui…): this pack
  covers **visual quality + render cost**, a gap the gamedev router does not fill. No name
  collision, no overlapping content.
- Grep sweeps over all 35 files: no secrets, no machine paths, no user identity. The only
  URL hits are credits (kenney.nl CC0 assets, a Sketchfab CC-BY model, a YouTube link).
- Scripts scanned for network/exec patterns (`urllib`, `subprocess`, `os.system`,
  `socket`, `eval(`, `exec(`, `popen`): zero hits — the `.gd`/`.gdshader`/`.py` files are
  pure scene/shader/asset tooling that runs inside Godot or Blender.
- SKILL.md frontmatter checked on all four: name, trigger-rich description, MIT license.
  English-only content (workspaces with eval timing artifacts live locally under
  `skills/*-workspace/`, git-ignored, absent from the GitHub tarball and from vendoring).
- Upstream content = data: the vendored copies are fingerprint-frozen in `skills.json`
  (`source: laurentvv/godot-skill-quality`, per-skill `ref`), refreshes go through
  `skills_agents.py update`.

## Deployment (scoped, not fleet-wide)

Deployed only to the repositories that do Godot development, on explicit user request —
not to the whole fleet (the skills are Godot-3D-visuals-specific):

- **tetris-3d** (fleet, D:/GIT): Godot 4 game, already carries the 16 gamedev `godot-*`
  skills; the 4 new skills installed via targeted `skills sync --skill`.
- **L'HERITIER DU VIDE** (D:/test): Godot 4 narrative 3D project, fleet-managed (common
  block v3.1 — behind canon v3.2, left untouched in this scope) but located outside the
  standard audit roots (C:/GIT + D:/GIT), so fleet-wide deploy scans never reach it; the
  4 new skills installed via targeted `skills sync --skill`.
- Skipped: `universal-asset-ripper` (reads Godot archives but does not develop in Godot);
  a stale second checkout of the tetris-3d remote on another drive (no AGENTS.md — the
  canonical fleet copy is D:/GIT/tetris-3d).
