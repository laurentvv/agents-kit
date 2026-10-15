# Sprint Progress — "duckdb state ledger"

## Current Goal
- [ ] Ship the DuckDB ledger (engine, migration, skill, canon v3.0) fully tested locally (done); the real migrations wait for the user's explicit GO.

## Iteration Milestones
- [x] F-14: state engine CLI (schema + operational commands)
- [x] F-15: transactional legacy migration (English + French legacy formats)
- [x] F-16: agent-state skill + byte-identical mirror + dogfood install
- [x] F-17: canon v3.0 registered, kit + template resynced, docs updated
- [x] F-18: gates updated (CI, AGENTS.md section 7, ignore files, guard SKIP)
- [x] F-19: rehearsal migration on a copy of the real kit ledger

## Contract Validation
- Criterion-by-criterion evidence recorded at closure (command run, exit code).
