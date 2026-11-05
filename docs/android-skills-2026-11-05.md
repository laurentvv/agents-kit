# android/skills onboarding audit — 2026-11-05

**Decision**: vendor the **complete set of 36 skills** from `android/skills` — Google's
official repository of agent skills for Android development (Apache-2.0, pinned
`bf68e2d66a992a1e6aeb7e9263293cc23fcbf475`, main pushed 2026-11-04, 10.3k stars).
439 files / ~4.5 MB total across 18 upstream category folders. No skip candidate: the set
is coherent (one platform), text-only, collision-free, and every skill passed the
pre-vendor review.

## What the pack is

SKILL.md-first agent skills (open agentskills.io standard) that ground LLMs in Android
workflows developer.android.com shows models underperform on — each skill ships its
SKILL.md plus `references/` doc trees distilled from official guidance, and some add
sample Kotlin/XML code and small stdlib tooling:

| Upstream category | Skills (files) |
|---|---|
| build-system | `agp-9-upgrade` (7) |
| camera | `camerax` (13) |
| cars | `android-for-cars-parked-apps` (2) |
| device-ai | `appfunctions` (7), `litert-lm` (3), `litert-runtime` (5), `ml-kit-genai-prompt-api` (7), `mlkit-agent-api` (3) |
| devtools | `android-cli` (1) |
| identity | `restore-credentials` (4), `verified-email` (8) |
| jetpack-compose | `adaptive` (17), `ink-app-builder` (9), `ink-custom-brush-builder` (6), `jetpack-compose-performance` (10), `migrate-xml-views-to-jetpack-compose` (8) |
| media | `media3-cast-integration` (4) |
| navigation | `navigation-3` (28), `navigation-event` (5) |
| performance | `anr-audit-and-fix` (4), `r8-analyzer` (9) |
| play | `engage-sdk-integration` (29), `play-billing-library-version-upgrade` (4), `play-policy-insights` (14) |
| profilers | `android-profiler` (26) |
| security | `android-intent-security` (1), `android-permissions-security` (5) |
| system | `edge-to-edge` (1), `glance-appwidget-updates-and-memory` (13), `glance-canonical-layouts` (88) |
| testing | `testing-setup` (5) |
| tv | `leanback-to-compose-tv-migration` (4) |
| wear | `wear-compose-m3` (53), `wear-widgets` (5) |
| xr | `display-glasses-with-jetpack-compose-glimmer` (26), `projected-hardware` (5) |

Upstream nests skills under category folders; the kit installs them **flat**
(`skills/<name>/`, name = last path segment). All 36 SKILL.md frontmatter `name:` fields
match their folder names (verified one by one), and every vendored `skills.json` entry
records the `folder` key (e.g. `jetpack-compose/adaptive`) — `update` re-imports from the
recorded folder, `--folder` discipline inherited from the 2026-10-31 impeccable lesson.

## Review before vendoring (§5/§6)

- Tarball fetched at the pinned SHA (`a1e8166eea5c…` archive hash recorded locally);
  content reviewed from the extracted tree BEFORE `skills add`.
- Injection sweep over all 328 upstream markdown files (325 of them vendored in
  the pack; the 3 extras are repo-level docs — README + issue templates, excluded
  correctly): zero true hits — the two grep hits are legitimate Android
  guidance (FCM token delivery in an app's own backend, WebAuthn credential flow).
- Secrets / machine paths / user identity: none. The only email addresses are Google's
  own doc placeholders (`jane.doe.246745@gmail.com`).
- URL inventory: all upstream-official (developer.android.com, androidx.dev,
  ai.google.dev, developer.chrome.com, perfetto, gradle, dagger, robolectric, W3C…) plus
  `example.com`-style placeholders. No third-party telemetry or analytics.
- Binary check: none — the one suspicious-looking file
  (`android-profiler/references/perfetto/bin/trace_processor`, no extension) is an
  11 KB ASCII **Python wrapper**, not a binary. No `.gitattributes` `-text` addition
  needed (all 439 files are text; `skills/** text eol=lf` covers them).
- Supply-chain scan of the runnable tooling (8 Python files):
  - `play-policy-insights/scripts/play_store_scraper.py` — urllib GET of **public**
    `play.google.com/store/apps/details` + `datasafety` pages for a package name the
    user supplies; the declared purpose of the skill. No secrets sent, no write.
  - `android-profiler/references/perfetto/bin/trace_processor` — downloads the real
    Perfetto `trace_processor_shell` v58.3 at first run from Google's official artifact
    store (`commondatastorage.googleapis.com/perfetto-luci-artifacts`), **sha256 pinned
    per platform** (mac/linux/windows/android), then executes it — the same
    external-first-run-dependency pattern as the impeccable engine. Nothing downloaded
    at vendor/deploy time.
- Shebang files: 6 (5 `play-policy-insights` scripts + the `trace_processor` wrapper);
  all committed `100755` via `git update-index --chmod=+x` — Windows local gates cannot
  prove the exec bit (2026-09-28 EXE001 lesson).
- Line endings: zero CRLF files in the tarball — pure LF content under
  `skills/** text eol=lf`, fingerprint-safe on fresh clones.
- Name collisions: none against the 88 skills already vendored; upstream last-segment
  names are unique within the repo.
- Upstream content = data: vendored copies are fingerprint-frozen in `skills.json`
  (`source: android/skills`, per-skill `ref` + `folder`); refreshes go through
  `skills_agents.py update`.

## Deployment

Fleet-wide at the next `skills deploy`/refresh cycle (ordinary vendored content; the
kit's `.agents-kit-ignore` opt-out remains available per repository). This cycle only
the kit's own dogfood install is synced.

## References

- Upstream NOTICE kept at `docs/upstream-notices/android-skills-NOTICE.md`, with the
  Apache-2.0 license text vendored alongside at
  `docs/upstream-notices/android-skills-LICENSE.txt` (§4 attribution for the
  redistribution — the upstream license lives at the repository root, which vendoring
  correctly does not copy).
- Upstream: https://github.com/android/skills — docs:
  https://developer.android.com/tools/agents/android-skills
