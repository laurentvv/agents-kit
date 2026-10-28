# DeepEval wiring recipes

Pin: **deepeval 4.3.2**, Apache-2.0, Python >= 3.9. Official docs fetched
2026-10-28; the 4.x docs churn fast (eval modes are new) - re-verify before
upgrading.

## Install (consuming repository only)

```bash
uv add deepeval
```

Per section 1 discipline: `uv`, never `pip install`. DeepEval stays a
dependency of the repository that runs the evals - never of the kit.

## pytest integration (verbatim from the docs)

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.metrics import GEval

def test_correctness():
    correctness_metric = GEval(
        name="Correctness",
        criteria="Determine if the 'actual output' is correct based on the 'expected output'.",
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        threshold=0.5,
    )
    test_case = LLMTestCase(input=..., actual_output=..., expected_output=...)
    assert_test(test_case, [correctness_metric])
```

## Metrics: LLM judge vs deterministic

Almost all predefined metrics use an LLM judge:

- `GEval` - LLM-as-judge with chain of thought; `model=` accepts a provider
  string **or any `DeepEvalBaseLLM`** instance.
- `AnswerRelevancyMetric` - judge, referenceless (`input` + `actual_output`).
- `FaithfulnessMetric` - judge by default; needs `retrieval_context`; eval
  modes `llm` / `hybrid` / `system_one`.
- `HallucinationMetric` - judge by default; needs `context`.

Judge-free options: `deepeval set-eval-mode system_one` runs the metric
library with no LLM API key at all ("judge-free" mode); ROUGE / BLEU / BLEURT
are available via the `scorer` module inside custom metrics.

## Local judge (the fleet default)

- **Ollama is first-class**: `deepeval set-ollama --model=<model>
  --base-url=http://localhost:11434` (configures LLM judges only - not
  embedding models).
- **llama.cpp `llama-server`**: subclass `DeepEvalBaseLLM` (implement
  `get_model_name()`, `load_model()`, `generate()`, async `a_generate()`)
  wrapping an OpenAI-compatible client, then pass it per metric:
  `AnswerRelevancyMetric(model=my_llm)`. Custom LLMs are **per-metric, never
  global**.
- Azure OpenAI: `deepeval set-azure-openai --base-url=<endpoint> --model=<model>`.
- No generic base-url env var and no `config.yaml` are documented in current
  docs - do not invent one; wire per metric.

## CI

```bash
deepeval test run test_ai_agent.py    # pytest wrapper: file, dir, or file::test
```

Failing metrics fail the build (assertion-based gating). Useful flags:
`-v` verbose, `-x` exit on first failure, `-n` parallel processes,
`-c` cache, `-i` ignore errors, `-r` repeat. Everything runs locally;
`--official` optionally uploads via a `CONFIDENT_API_KEY` (never required).

UNVERIFIED: no JUnit output flag is documented in 4.x (docs and a code search
are both negative). Tests are plain pytest tests, so `pytest --junitxml` is
the expected route - confirm once in the consuming repo before wiring a CI
report step.

## Sources (fetched 2026-10-28)

- https://deepeval.com/docs/getting-started - install + first test
- https://deepeval.com/docs/metrics-introduction - metric taxonomy, eval modes
- https://deepeval.com/docs/metrics-llm-evals - GEval
- https://deepeval.com/docs/metrics-answer-relevancy - /metrics-faithfulness - /metrics-hallucination
- https://deepeval.com/docs/command-line-interface - `test run`, `set-ollama`
- https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd - CI mode
- https://github.com/confident-ai/deepeval - README, Apache-2.0
