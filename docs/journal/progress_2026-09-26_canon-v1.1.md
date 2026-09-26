# Sprint Progress

> Translated from French on 2026-09-26 (English sprint); file names, CLI flags, test names and state labels use their current v2.0 names.

## Current Goal
- [x] "canon v1.1" sprint: fill the gaps of the common block found in review and during the tooling sprint, with no loss for the fleet (v1.0 → v1.1 through `sync`).

## Iteration Milestones
- [x] F-09 Tests independent of the canon version
- [x] F-10 Canon v1.1
- [x] F-11 v1.1 propagation and documentation

## Contract Validation (2026-09-26)
- K01-K02: `version` exit 0; registry v1.0 = 7b36d6d3… (unchanged), v1.1 = 7b633d73…; `sync` refused (exit 2) before registration.
- K03: `check .` and `check . --file template/AGENTS.template.md` → UP TO DATE (v1.1).
- K04-K05: simulated fleet from `git show` v1.0: "behind" → `sync` → v1.1, §7 identical (`cmp`); edited v1.0 block → REFUSED, local line kept.
- K06-K14: reviewed in the canon (Priority header, §1 encoding, §2 proportionality + contract lifecycle, §3 pinned Gate + Closure, §4, §5, §6).
- K15-K16: `test_canon_is_generic` + `test_canon_is_lean_and_clean` green; block = 7 675 bytes.
- K17: 43 tests green on v1.0 (before the bump), then on v1.1; no hardcoded version (grep).
- K18: unittest, `ruff@0.16.9` (and 0.15.8), `ledger . --strict` green locally; GitHub CI checked after push (recorded in `log.md`: 661d531 fully green).
- Gap found and fixed: `ledger` treated contract archiving (v1.1 Closure) as an error → aligned, test added.
