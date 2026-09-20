# 第三周阅读：Tool Use、Function Calling、MCP、Sandbox 与 Retry

[English](week03-tool-use-and-harness.md) | [简体中文](week03-tool-use-and-harness.zh-CN.md)

> 整理日期：2026-09-20。CS329Z 的 Tool Use & Function Calling 课程安排在 2026-10-05；
> 截至整理时，课程页列出的指定阅读是 MCP Specification，讲义可能尚未发布。

## 学习目标

阅读结束后，应该能够解释：

1. 模型的 `tool_call` 只是一个结构化请求，真正执行工具的是 Harness。
2. JSON Schema 能约束模型输出，但宿主程序仍必须再次校验名称、参数和权限。
3. MCP 标准化的是 Host、Client、Server 之间的能力发现和调用，不是 Agent 的全部运行时。
4. Sandbox 是技术执行边界，approval 是授权决策；二者不能互相替代。
5. Retry 只适合暂时性失败，参数错误、权限错误和业务错误不应原样盲目重试。

## 必读顺序

### 1. CS329Z Week 3 课程页

- [Stanford CS329Z: Engineering AI Agents](https://cs329z.stanford.edu/)
- 重点：Tool use、function-calling APIs、MCP、tool design、code-execution sandbox、error
  handling 和 retries。
- 课程实践目标：不依赖 Agent framework，从零构建 tool-using system。

### 2. MCP Specification

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices)

阅读重点：

- MCP 使用 JSON-RPC 2.0 连接 Host、Client 与 Server。
- Server 可以暴露 Resources、Prompts 和 Tools；tool 通过 `inputSchema` 描述参数。
- `tools/list` 用于发现能力，`tools/call` 用于执行能力。
- Tool execution error 应作为可操作的反馈返回模型；协议级错误通常更难由模型修正。
- Client 仍需执行输入/输出校验、timeout、审计日志和敏感操作确认。

### 3. Function Calling 与结构化输出

- [Ollama Tool Calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Claude Tool Reference](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference)

本仓库这一版没有把 Harness 绑定到某一家模型 API。模型返回统一动作：

```json
{"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "6*7"}}
```

或者：

```json
{"type": "finish", "answer": "6 * 7 = 42"}
```

Ollama 的 `format` 接收 JSON Schema，帮助模型生成合法动作；随后
`parse_action()` 在本地再次验证。Provider-side constrained generation 不是安全边界。

### 4. Claude Harness 与工具设计

- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Writing Effective Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Scaling Managed Agents: Decoupling the Brain from the Hands](https://www.anthropic.com/engineering/managed-agents)

借鉴的三个原则：

- Agent loop 可以保持简单：模型和工具调用交替进行，并从环境取得 ground truth。
- 工具是确定性系统与非确定性模型之间的契约，名称、描述、参数边界和错误必须清楚。
- 将 session event log、Harness 和执行工具的 sandbox 分离，让任何一层都可以失败或替换。

### 5. Codex Harness 与权限边界

- [Codex as a Platform](https://developers.openai.com/blog/codex-as-a-platform)
- [Agents API Architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture)
- [Agent Approvals & Security](https://learn.chatgpt.com/docs/agent-approvals-security)

Codex 的公开架构把职责拆为 Harness、Environment/Sandbox 和应用服务器。Sandbox mode
决定一项操作在技术上能否执行，approval policy 决定何时必须向用户请求授权。本实验先实现工具
allowlist 和硬预算，后续再加入交互式 approval。

### 6. Sandbox

- [Claude Code Sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing)

真正的 sandbox 至少需要 filesystem isolation 和 network isolation，并应覆盖工具启动的子进程。
本实验的 `RestrictedPythonTool` 只采用 AST allowlist、隔离子进程、临时工作目录、`-I -S` 和
timeout，适合学习和测试，但**不是生产安全边界**。后续应替换为容器、VM、macOS Seatbelt 或
Linux bubblewrap/seccomp 等 OS 级机制。

### 7. Error Handling 与 Retry

- [Claude API Errors](https://platform.claude.com/docs/en/api/errors)

推荐分类：

| 错误 | 处理方式 |
| --- | --- |
| 连接中断、timeout、429、部分 5xx | 有上限的 exponential backoff，并尊重 `retry-after` |
| JSON/schema 不合法 | 作为 Observation 返回模型，让模型修正动作 |
| 工具参数或业务规则错误 | 返回明确错误，不自动重复同一调用 |
| 权限拒绝 | fail closed，等待授权或选择其他方案 |
| 预算耗尽 | 立即终止并记录 `budget_exhausted` |

## 本仓库实现映射

```text
User Task
   ↓
observe        ← 从 append-only event log 构造有界 context view
   ↓
decide         ← 模型只返回 tool_call 或 finish JSON
   ↓
validate       ← schema、tool allowlist、参数、步数/token/时间/成本预算
   ↓
act            ← Harness 调用确定性 Tool adapter
   ↓
Observation    ← 结果或可修正错误写入 JSONL
   ↓
continue/stop  ← success、failure 或 budget_exhausted
```

代码入口：

- `src/verifiable_agent_lab/harness/loop.py`：主循环和预算。
- `src/verifiable_agent_lab/harness/schema.py`：动作与参数验证。
- `src/verifiable_agent_lab/harness/tools.py`：工具注册和三个工具。
- `src/verifiable_agent_lab/harness/events.py`：append-only JSONL trace。
- `src/verifiable_agent_lab/harness/backends.py`：Ollama 和确定性 fixture provider。

## 阅读问题

1. 为什么不能因为模型 API 已启用 strict/schema output 就删除本地验证？
2. Tool execution error 和 protocol error 中，哪一种更适合交给模型自我修正？
3. 为什么“每次都请求批准”仍然不等于 sandbox？
4. 哪些错误可以自动 retry？重试有副作用的工具前还缺少什么机制？
5. JSONL event log 与当前 context window 为什么应是两个不同对象？
