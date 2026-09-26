# Measurement: token cost — French vs English, and where tokens really go

Question: should the common block move to English to consume fewer tokens?
Measured on 2026-09-26 on the common block v1.1 (French) and on a faithful English translation (same rules, same structure, same markers). The user then chose English: that translation became **v2.0**.

## 0. Result of the switch (v1.1 French → v2.0 English)

| Tokenizer | v1.1 (French) | v2.0 (English) | Change |
|---|---:|---:|---:|
| o200k (GPT-4o / Codex) | 1 941 | 1 623 | −16 % |
| cl100k (GPT-4) | 2 140 | 1 618 | −24 % |
| Claude (legacy tokenizer) | 2 369 | 1 746 | −26 % |
| Qwen 2.5 | 2 135 | 1 626 | −24 % |
| Llama 3.1 | 2 137 | 1 619 | −24 % |

Block size: 7 675 → 6 779 bytes. Saving: **~320 to ~620 tokens per session**, in every repository of the fleet.

## 1. Common block: French vs English (measured before the switch)

| Tokenizer | French | French, ASCII punctuation | English | English vs French |
|---|---:|---:|---:|---:|
| o200k (GPT-4o / Codex) | 1 941 | 1 939 | 1 625 | −16 % |
| cl100k (GPT-4) | 2 140 | 2 139 | 1 620 | −24 % |
| Claude (legacy tokenizer) | 2 370 | 2 370 | 1 748 | −26 % |
| Qwen 2.5 | 2 135 | 2 134 | 1 628 | −24 % |
| Llama 3.1 | 2 137 | 2 136 | 1 621 | −24 % |

- English saves **16 to 26 %**.
- Replacing typography (`—`, `→`, French quotation marks, `·`, `…`) with ASCII changes **nothing** (≤ 2 tokens).

## 2. What is loaded in every session (same method, French texts of the time)

| Item read in every session | Bytes | o200k | Claude (legacy) |
|---|---:|---:|---:|
| Common block v1.1 (French) | 7 676 | 1 941 | 2 370 |
| Full kit AGENTS.md (block + §7) | 13 430 | 3 499 | 4 214 |
| `log.md` at the canon's rotation threshold (~150 KB)* | 153 600 | 49 971 | 56 152 |
| `log.md` capped at 20 KB* | 20 480 | 6 662 | 7 488 |
| 56 KB AGENTS.md (ai-doc2video case from the audit)* | 57 344 | 14 915 | 17 965 |
| AGENTS.md cut to 20 KB (the audit's target)* | 20 480 | 5 281 | 6 395 |

\* Extrapolated: real kit content (`log.md` entries, AGENTS.md text) repeated up to the given size.

## 3. Levers ranked by gain per session

| Lever | Estimated gain (o200k → Claude legacy) |
|---|---:|
| Cap the `log.md` read at bootstrap (150 KB → ~20 KB, or "last N entries") | **~43 000 → ~49 000** |
| Slim oversized §7 parts (56 KB → 20 KB, long context to `PROJECT_MEMORY.md`) | **~9 600 → ~11 600** |
| Translate the common block to English (done in v2.0) | ~320 → ~620 |
| ASCII typography | ~0 |

## Method and limits

- Offline tokenizers from npm: `gpt-tokenizer` 4.0.0 (o200k, cl100k), `@anthropic-ai/tokenizer` 0.0.4, `@lenml/tokenizer-qwen2_5` and `@lenml/tokenizer-llama3_1` 3.7.2.
- The published Claude tokenizer is the Claude 2-era one: Anthropic states it is not exact for current models. It only shows a trend; an exact count needs the `count_tokens` API, not available here (no key).
- Agents cache their stable prefix (system instructions + AGENTS.md): the billed cost goes down, but the space taken in the context window stays the same.
