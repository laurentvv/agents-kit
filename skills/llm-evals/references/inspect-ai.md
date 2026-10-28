# Inspect AI wiring recipes

Pin: **inspect-ai 0.3.285**, MIT, **Python >= 3.11** (check the consuming
repository's Python before reaching for it - it disqualifies older repos).
Official docs fetched 2026-10-28; docs are versioned with releases, so pin
the doc tag matching the installed version.

## Install (consuming repository only)

```bash
uv add inspect-ai      # pip name is hyphenated, import name is inspect_ai
```

## Core anatomy (verbatim from the tutorial)

```python
@task
def capitals():
    return Task(
        dataset=[Sample(input="What is the capital of France?", target="Paris")],
        solver=generate(),
        scorer=match(),
    )
```

The tutorial's first real task chains solvers
(`solver=[system_message(SYSTEM_MESSAGE), generate()]`) and grades with
`model_graded_fact()`; multiple-choice evaluation pairs the
`multiple_choice()` solver with the `choice()` scorer.

## Run and inspect

```bash
inspect eval security_guide.py --model openai/gpt-5
inspect eval security_guide.py --model <local> --model-role grader=<local-judge>
inspect view          # browser UI over ./logs, auto-updating
```

Python API: `eval(task, model=...)`.

## Local providers (the fleet default)

- **llama.cpp `llama-server`**: generic OpenAI-compatible provider
  `openai-api/llamacpp/<model>` with `LLAMACPP_BASE_URL=http://localhost:8080/v1`
  (env convention: `<PROVIDER_NAME>_API_KEY` / `<PROVIDER_NAME>_BASE_URL`,
  hyphens become underscores). `openai-api-completions/...` targets the legacy
  `/v1/completions` route.
- **Ollama**: `ollama/<model>` + `OLLAMA_BASE_URL`
  (default `http://localhost:11434/v1`).
- Plain `openai/` honors `OPENAI_API_KEY` + `OPENAI_BASE_URL`;
  `vLLM` (`VLLM_BASE_URL` or `--model-base-url`) and
  `llama-cpp-python` (`LLAMA_CPP_PYTHON_BASE_URL`) also ship built-in.
- UNVERIFIED: a `vllext` provider name appears in older notes but not in the
  current docs - use `openai-api/...` instead.

## Built-in scorers

`includes()`, `match()`, `pattern()`, `answer()`, `exact()`, `f1()`,
`choice()` (pairs with `multiple_choice()`; multi-answer targets like "A,B"),
`math()`, `perplexity()`, `target_perplexity()`; model-graded
`model_graded_qa()` / `model_graded_fact()`; custom via the `@scorer`
decorator.

## Sandboxing (no Docker required)

Two built-in sandbox types: `docker` and **`local`** ("Local file system (no
sandbox)") - `local` keeps Windows machines in the game without Docker
Desktop. A sandbox must be declared explicitly (at sample, task or eval
level, e.g. `sandbox="docker"` or `sandbox=("docker", "compose.yaml")`)
whenever tools use `sandbox()`. If Docker is used: Engine >= 24.0.6, Compose
>= 2.21.0. UNVERIFIED: no Windows-specific sandbox guidance is documented.

## Sources (fetched 2026-10-28)

- https://inspect.aisi.org.uk/ - landing + tutorial
- https://inspect.aisi.org.uk/tutorial.html.md - first task
- https://inspect.aisi.org.uk/providers.html.md - provider list, local endpoints
- https://inspect.aisi.org.uk/standard-scorers.html.md - scorers
- https://inspect.aisi.org.uk/sandboxing.html.md - sandboxes
- https://github.com/UKGovernmentBEIS/inspect_ai - README, MIT
