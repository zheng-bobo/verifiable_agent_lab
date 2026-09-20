# Week 3 Reading: Tool Use, Function Calling, MCP, Sandboxing, and Retries

[English](week03-tool-use-and-harness.md) | [简体中文](week03-tool-use-and-harness.zh-CN.md)

> Compiled on September 20, 2026. CS329Z schedules Tool Use & Function Calling for
> October 5, 2026. At the time of writing, the course page lists the MCP Specification as the
> required reading; lecture slides may not have been released yet.

## Learning objectives

After these readings, you should be able to explain that:

1. A model `tool_call` is a structured request; the harness performs the actual execution.
2. Provider-side JSON Schema helps generation, but the host must still validate names,
   arguments, permissions, and budgets.
3. MCP standardizes capability discovery and invocation between hosts, clients, and servers; it
   is not the entire agent runtime.
4. A sandbox is a technical execution boundary, while approval is an authorization decision.
5. Retries belong to transient failures, not unchanged permission, validation, or business errors.

## Reading order

### 1. CS329Z Week 3

- [Stanford CS329Z: Engineering AI Agents](https://cs329z.stanford.edu/)
- Focus: tool use, function-calling APIs, MCP, tool design, code-execution sandboxes, error
  handling, and retries.
- Practice goal: build a tool-using system from scratch without an agent framework.

### 2. MCP Specification

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices)

Focus on JSON-RPC, host/client/server roles, `tools/list`, `tools/call`, input and output schemas,
the distinction between protocol and execution errors, consent, timeouts, validation, and audit
logging.

### 3. Function calling and structured output

- [Ollama Tool Calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Claude Tool Reference](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference)

This repository uses a provider-neutral action contract:

```json
{"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "6*7"}}
```

or:

```json
{"type": "finish", "answer": "6 * 7 = 42"}
```

Ollama receives the action JSON Schema through `format`, and `parse_action()` validates the
result again locally. Provider-side constrained generation is not a security boundary.

### 4. Claude harness and tool design

- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Writing Effective Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Scaling Managed Agents: Decoupling the Brain from the Hands](https://www.anthropic.com/engineering/managed-agents)

The implementation borrows three ideas: keep the agent loop composable; treat tools as contracts
between deterministic software and a nondeterministic model; and separate the durable session log,
harness, and execution environment.

### 5. Codex harness and permission boundaries

- [Codex as a Platform](https://developers.openai.com/blog/codex-as-a-platform)
- [Agents API Architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture)
- [Agent Approvals & Security](https://learn.chatgpt.com/docs/agent-approvals-security)

The public Codex architecture separates the harness, environment/sandbox, and application server.
Sandbox mode determines what can technically execute; approval policy determines when user
authorization is required. This iteration implements an allowlist and hard budgets; interactive
approval is a later milestone.

### 6. Sandboxing

- [Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)

A real sandbox requires both filesystem and network isolation and must cover child processes. The
repository's `RestrictedPythonTool` only combines AST allowlisting, an isolated subprocess, a
temporary working directory, `-I -S`, and a timeout. It is useful for learning and tests, but it is
**not a production security boundary**.

### 7. Error handling and retry

- [Claude API Errors](https://platform.claude.com/docs/en/api/errors)

Use bounded exponential backoff for transient connection, timeout, rate-limit, and selected server
errors. Return schema or argument failures as observations so the model can change its action. Fail
closed on permission errors, and stop immediately when a harness budget is exhausted.

## Repository mapping

```text
User Task
   ↓
observe        ← build a bounded context view from the append-only event log
   ↓
decide         ← model returns one tool_call or finish JSON object
   ↓
validate       ← schema, allowlist, arguments, and step/token/time/cost budgets
   ↓
act            ← harness invokes a deterministic tool adapter
   ↓
Observation    ← append the result or actionable error to JSONL
   ↓
continue/stop  ← success, failure, or budget_exhausted
```

Start with `src/verifiable_agent_lab/harness/loop.py`, then read `schema.py`, `tools.py`,
`events.py`, and `backends.py`.
