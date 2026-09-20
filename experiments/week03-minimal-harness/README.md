# Week 3: Minimal Agent Harness

[English](README.md) | [简体中文](README.zh-CN.md)

This experiment borrows the public harness boundaries described by Claude and Codex and implements
the following loop from scratch:

```text
User Task → observe → decide → validate → act → Observation → continue/stop
```

It does not use LangChain, LangGraph, or another agent framework.

## Offline smoke test

```bash
python experiments/week03-minimal-harness/run.py --backend fixture
```

The fixture deterministically calls `document_search`, `calculator`, and `finish`. It verifies the
loop, budgets, and JSONL trace; it is not a model-quality result.

## Ollama run

```bash
ollama pull qwen3-embedding:0.6b
ollama pull qwen3:4b
python experiments/week03-minimal-harness/run.py --backend ollama
```

The embedding model indexes notes and embeds search queries. The generation model reads the task,
tool schemas, and observations, then requests one `tool_call` or `finish` action.

```bash
python experiments/week03-minimal-harness/run.py \
  --backend ollama \
  --task "Search the notes for MCP versus function calling, then calculate (18 + 24) / 2"
```

Each run writes an ignored trace under `runs/week03-minimal-harness/*.jsonl`.

## Tools and boundaries

| Tool | Purpose | Boundary |
| --- | --- | --- |
| `document_search` | Reuse the Week 2 exact-vector RAG index | Read-only; at most eight chunks |
| `calculator` | AST arithmetic without `eval` | Small operator and finite-value allowlist |
| `python_runner` | Pure computations and assertions | No imports, attributes, file/network calls; timeout |

The Python runner is a teaching restriction, not an OS-level security sandbox.

The model selects an exposed tool, proposes arguments, or asks to finish. The harness owns the
tool allowlist, local schema validation, execution, bounded retry, budgets, logging, and terminal
status. Transient infrastructure errors use bounded exponential backoff. Validation and business
errors become observations so the model can change its action; they are not blindly replayed.

## Reading order

1. `src/verifiable_agent_lab/harness/loop.py`
2. `src/verifiable_agent_lab/harness/types.py`
3. `src/verifiable_agent_lab/harness/schema.py`
4. `src/verifiable_agent_lab/harness/tools.py`
5. `src/verifiable_agent_lab/harness/events.py`
6. `src/verifiable_agent_lab/harness/backends.py`
7. `experiments/week03-minimal-harness/run.py`

Companion notes: [Tool Use, Function Calling, MCP, Sandboxing, and Retries](../../docs/readings/week03-tool-use-and-harness.md).

## Current limitations

- Runs cannot yet recover across processes; session recovery belongs to Week 4.
- The context view keeps recent observations; compaction and structured handoff are not implemented.
- There is no interactive approval UI; startup tool allowlisting is the current permission policy.
- Ollama JSON Schema constrains generation but does not replace host-side validation.

## Observed failure case

In a local `qwen3:4b-instruct` run, an initially generic action schema constrained `arguments` only
to an object. The model incorrectly wrapped inputs as `{"tool": ..., "input": ...}`. Embedding each
tool's `input_schema` directly in the action schema fixed argument generation. The model may still
repeat an identical successful retrieval; the prompt tells it to use existing observations, while
`max_steps` remains the deterministic infinite-loop guard.
