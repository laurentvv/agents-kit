# MCP fleet rollout - 2026-10-18

First deployment of the fourth kit concern: the **MCP fleet CLI** (`scripts/mcp_agents.py`,
skill `agent-mcp`). This note records the real-machine verification required by the kit's
validation rules (every verdict backed by an executed command), the fleet rollout result,
and the drift the first `doctor` run immediately surfaced. User-profile paths are redacted
as `~` in this committed note; raw outputs stay local (`scratch/mcp-evidence/`).

## What runs where (this machine, local descriptor)

Two entries declared in the local `mcp-fleet.local.yml` (never committed):

- `hister` - local HTTP search daemon on `127.0.0.1:4433`, the fallback path of the
  knowledge-router MCP. Probed by URL; `start`/`stop` through the declared `.cmd`
  scripts; referenced paths extracted from its `~/.config/hister/config.yml`.
- `knowledge-router` - stdio MCP whose fast path is the `md-doc-search` Rust binary.
  Probed by command (`md-doc-search.exe --version`); corpus freshness on
  `docs/*/BUILT_AT.txt` (45-day budget); referenced paths extracted from the router's
  `config.py` defaults.

## Verification evidence (redacted)

**1. Down daemon + index drift caught (exit 1)** - the daemon had been down for days and
nothing flagged it; `doctor` now does:

```
$ mcp_agents.py doctor        # exit code 1
hister: UNHEALTHY
  probe:    down     [url] <urlopen error ... connection refused>
  referenced: MISSING <repo>/gd-agentic-skills
  referenced: MISSING <repo>/MoneyPrinterV2
  referenced: MISSING <repo>/jev-ai
knowledge-router: HEALTHY
  probe:    up       [command] md-doc-search 0.2.1
  freshness: fresh (newest marker 544.1 h old, budget 1080 h)
doctor: 1/2 healthy (mcp-fleet.local.yml)
```

The three MISSING lines are real config drift: the daemon's indexer still references
directories that were renamed or deleted. The verdict stays UNHEALTHY until the config
is cleaned - by design, this is a finding for the owner, not an auto-fix.

**2. Lifecycle verified on the real daemon** - the declared `start` command (a detached
`.cmd` launcher) returns exit 0 and the daemon answers HTTP 200:

```
$ mcp_agents.py start hister        # exit code 0
  $ cmd /c start "hister" /min <tools>/start-hister.cmd
start hister: done

$ mcp_agents.py probe hister
  probe:    up       [url] HTTP 200
```

The first attempt used the bare `.cmd` (which runs `hister.exe listen` in the
foreground): the CLI blocked on it. Lesson folded into the descriptor: a lifecycle
command must DETACH (`cmd /c start ... /min` on Windows) so the CLI returns.

**3. Up path stays green** - `knowledge-router` reports HEALTHY (fast-path binary runs,
corpus markers within budget, all referenced paths exist), which is exactly the state
`doctor` should report while only the fallback daemon is down.

## Fleet rollout

```
$ skills_agents.py deploy --skill agent-mcp     # kit installed into the fleet repos
$ skills_agents.py check <repo>                 # up_to_date on each target
```

- The deploy applied the skill to every fleet repository that already has
  `.agents/skills` (42 repositories, on-disk installs). Since canon v3.1 made
  `.agents/` local-only (git-ignored), these installs are invisible to git:
  no deploy commit is needed anywhere anymore.
- Required targets verified `up_to_date` with a byte-identical script:
  `knowledge-router-mcp` and `md-doc-search`.
- Both repositories can adopt the CLI by copying `template/mcp-fleet.template.yml` to
  their own local `mcp-fleet.local.yml` (or by pointing `MCP_FLEET_CONFIG` at the kit's).

## Remaining actions for the owner

1. Clean the 3 dead directories out of the daemon's indexer config, then restart it
   through the declared lifecycle commands - `doctor` flips to 2/2.
2. Optional: schedule `doctor` (CI or cron) so a down daemon is flagged within minutes
   instead of days.
