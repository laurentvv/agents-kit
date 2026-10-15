# Sprint Progress — "duckdb state ledger"

## Current Goal
- [ ] Ship the DuckDB ledger (engine, migration, skill, canon v3.0) fully tested locally; the real migrations wait for the user's explicit GO.

## Iteration Milestones
- [ ] F-14: state engine CLI (schema + operational commands)
- [ ] F-15: transactional legacy migration (English + French legacy formats)
- [ ] F-16: agent-state skill + byte-identical mirror + dogfood install
- [ ] F-17: canon v3.0 registered, kit + template resynced, docs updated
- [ ] F-18: gates updated (CI, AGENTS.md section 7, ignore files, guard SKIP)
- [ ] F-19: rehearsal migration on a copy of the real kit ledger

## Contract Validation
- Criterion-by-criterion evidence recorded at closure (command run, exit code).
