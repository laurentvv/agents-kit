# Promptfoo wiring recipes

Pin: **promptfoo 0.125.1**, MIT license. Official docs fetched 2026-10-28;
re-verify before a major upgrade. Binaries `promptfoo` and `pf`.

## Install

```bash
npm install -g promptfoo        # or per-run: npx promptfoo@latest
promptfoo init --example getting-started
```

CI docs recommend Node >= 22 (24 LTS preferred).

## Local endpoints (the fleet default)

**llama.cpp `llama-server`** (`http://localhost:8080/v1`) - generic
OpenAI-compatible provider:

```yaml
providers:
  - id: openai:chat:my-local-model
    config:
      apiBaseUrl: http://localhost:8080/v1
      apiKeyRequired: false        # do not demand an OpenAI key
      useDefaultApiKey: false
```

The `openai` provider resolves its base URL from `OPENAI_API_BASE_URL`, then
`OPENAI_BASE_URL`, then `OPENAI_API_HOST`; per-provider `apiKeyEnvar` is
supported. The native `llama` provider (llama.cpp `/completion` endpoint)
reads only the env var `LLAMA_BASE_URL` (default `http://localhost:8080`) -
its `config.baseUrl` is ignored.

**Ollama**: provider `ollama:chat:<model>`, env `OLLAMA_BASE_URL`
(default `http://localhost:11434`).

## Minimal configuration (verbatim from the docs)

```yaml
prompts: [prompt.txt]
providers: [openai:gpt-4o-mini]
tests:
  - vars:
      language: English
      topic: the tech industry
    assert:
      - type: contains
        value: "London"
      - type: javascript
        value: output.length > 400
      - type: llm-rubric
        value: Is spoken like a pirate
      - type: similar
        value: "The tech industry is a sector..."
        threshold: 0.6
defaultTest:
  options:
    provider:
      id: 'openai:chat:gpt-4.1'   # grader override - judge can differ from target
      config:
        temperature: 0
```

Swap the provider for a local endpoint id (above) to run everything on
llama.cpp or Ollama.

## Assertion taxonomy

- **Deterministic**: `contains` / `contains-any` / `contains-all` /
  `contains-json`, `equals`, `is-json`, `javascript`, `python`, `regex`,
  `similar` (embeddings-based), cost and latency checks.
- **Model-graded (LLM judge)**: `llm-rubric`, `agent-rubric`, `search-rubric`,
  `model-graded-closedqa`, `factuality`, `g-eval`, `answer-relevance`,
  `classifier`, `moderation`, `select-best`, `max-score`, `pi`.
- **RAG context**: `context-recall`, `context-relevance`,
  `context-faithfulness`.
- **Conversational / trajectory**: `conversation-relevance`,
  `trajectory:goal-success`.

Grader precedence: `--grader` CLI flag > assertion `provider` >
`test.options.provider` > `defaultTest.options.provider` - point the grader at
a local model even when the target under test is remote.

## CI invocation

```bash
npx promptfoo@latest eval -c promptfooconfig.yaml -o results.json -o report.html -o results.junit.xml --no-progress-bar
```

Output formats: csv, txt, json, jsonl, yaml, html, xml, junit.xml (multiple
`-o` flags allowed). **Exit codes**: 100 when at least one test fails (or the
pass rate drops below `PROMPTFOO_PASS_RATE_THRESHOLD`), 1 for other errors;
overridable via `PROMPTFOO_FAILED_TEST_EXIT_CODE`. UNVERIFIED: one docs page
says exit 1 on failure while the CLI reference says 100 - assert the actual
exit code once in the consuming repo before gating CI on it. GitHub Action:
`promptfoo/promptfoo-action@v1`.

## Red-teaming (local, OSS)

The scanner runs locally on the machine; the paid cloud is only for hosted
sharing:

```bash
promptfoo redteam setup                    # web wizard
promptfoo redteam init --no-gui            # config without the wizard
promptfoo redteam run && promptfoo redteam report
```

Generated test cases land in `redteam.yaml` / `promptfooconfig.yaml`.

## Sources (fetched 2026-10-28)

- https://www.promptfoo.dev/docs/intro/ - quickstart
- https://www.promptfoo.dev/docs/configuration/guide/ - config reference
- https://www.promptfoo.dev/docs/providers/openai/ - OpenAI-compatible provider
- https://www.promptfoo.dev/docs/providers/llama.cpp/ - llama.cpp provider
- https://www.promptfoo.dev/docs/providers/ollama/ - Ollama provider
- https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/ - assertions
- https://www.promptfoo.dev/docs/integrations/ci-cd/ + /docs/usage/command-line/ - CI and exit codes
- https://www.promptfoo.dev/docs/red-team/quickstart/ - red-teaming
- https://github.com/promptfoo/promptfoo - README, MIT license
