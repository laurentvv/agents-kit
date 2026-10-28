# LLM eval tooling audit — 2026-10-28

Evaluation of the five repositories surfaced on 2026-10-28 (self-refine,
reflexion, deepeval, promptfoo, inspect_ai), the use / skip decision taken
for each, and the resulting authored `llm-evals` skill. All framework facts
were verified against the official documentation fetched 2026-10-28 (§6
discipline); none of the tools is vendored — they enter consuming
repositories as dependencies.

## Decision table

| Repository | Decision | Reason | Pinned version | License |
|---|---|---|---|---|
| promptfoo/promptfoo | **USE — default pick** (guidance in the `llm-evals` skill) | Best fit for the fleet: native wiring of local OpenAI-compatible endpoints (llama.cpp `llama-server`, Ollama), YAML-driven prompt regression, deterministic + LLM-graded assertions, exit-code CI gating, red-teaming that runs locally in the OSS CLI | `0.125.1` (npm, 2026-10-28) | MIT |
| confident-ai/deepeval | **USE — pytest repos** (guidance in the skill) | Semantic metrics as pytest asserts (G-Eval, faithfulness, hallucination); local judge first-class on Ollama, per-metric `DeepEvalBaseLLM` for llama.cpp; judge-free `system_one` mode runs with no API key | `4.3.2` (PyPI, 2026-10-28) | Apache-2.0 |
| UKGovernmentBEIS/inspect_ai | **USE — agent evals** (guidance in the skill) | The only one of the three built for evaluating *agents* (task → solver → scorer, sandboxes, `inspect view`); `local` sandbox works without Docker (Windows-friendly); **requires Python ≥ 3.11** — check per repo | `0.3.285` (PyPI, 2026-10-28) | MIT |
| madaan/self-refine | **SKIP** (research artifact) | NeurIPS 2023 paper code, dormant since publication; not a maintained library, ships no SKILL.md (not vendorable via `skills add`). The iterate-with-self-feedback pattern is already carried by the canon's execution loop (§3: action → gate → sync) and the `reality-checker` skill | — (not vendored) | research code |
| noahshinn/reflexion | **SKIP** (research artifact) | Same profile as self-refine. Its core idea — verbal reflection after failure — is already embodied fleet-wide by external feedback loops: agent-run PR review (§4) beats self-feedback, which is exactly Reflexion's own lesson | — (not vendored) | research code |

## Why an authored skill instead of vendoring

The three frameworks ship no `SKILL.md` skills (the `skills add` pipeline
requires them — discovery in `scripts/skills_agents.py`), so vendoring is
structurally impossible; and the kit's zero-dependency invariant forbids
adopting them as kit dependencies anyway. The useful capture is the
**selection knowledge and the pinned wiring recipes** — delivered as the
authored `llm-evals` skill (SKILL.md + 3 reference files, doc-only, no
script, no new write path). The tools themselves enter a consuming repository
only when that repository adopts evals (`uv add deepeval` / `uv add
inspect-ai` / `npm install promptfoo`), one tool per repository.

## Fleet candidate repositories (2026-10-28 fleet map)

- **Promptfoo** — `Prompt-Vault` + `AIFeeder` (prompt collections to
  regression-test), `trad-fr-to-en` / `gen-cv` (llama.cpp local servers),
  `rag-ollama`, `bench-ai` / `compare-IA-decision` (quality side of the
  benches, complementing the performance side they already cover).
- **DeepEval** — pytest repos testing LLM outputs: `postfix-log` (AI
  fallback engine), `ocr-to-validation` (calibrated classification outputs),
  `trad-fr-to-en` / `gen-cv` again (Python + local judge).
- **Inspect AI** — agent repos with Python ≥ 3.11:
  `graph-orchestrator-smolagents`, `computer-use`, `oil-agent`,
  `arxiv-editorial-agent` / `news-editorial-agent` (watch loops). The Python
  ≥ 3.11 floor disqualifies older repos — check before wiring.

## Unverified points (flagged in the reference files)

- Promptfoo exit code on failure: docs disagree (1 vs 100; the CLI reference
  says 100, overridable) — assert once in the consuming repo before gating CI.
- DeepEval JUnit output: no flag documented in 4.x; the `pytest --junitxml`
  route is inference, not doc-verified.
- Inspect AI: no Windows-specific sandbox guidance documented; the `vllext`
  provider name found in older notes is absent from current docs.

## Fleet notes

- Deploys with the standard `skills_agents.py sync <repo>` cycle; nothing
  changes for consumers that opt out via `.agents-kit-ignore`.
- Adoption stays a per-repository decision (its own sprint in that repo's
  ledger); the kit ships guidance, not dependencies. A promptfoo pilot
  (Prompt-Vault or a local-llama repo) is the natural first wiring, as its
  own small PR in the target repository.
