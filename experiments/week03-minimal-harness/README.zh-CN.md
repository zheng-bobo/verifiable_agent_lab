# 第三周：最小 Agent Harness

[English](README.md) | [简体中文](README.zh-CN.md)

这个实验借鉴 Claude 与 Codex 公开的 Harness 边界设计，从零实现：

```text
User Task → observe → decide → validate → act → Observation → continue/stop
```

没有使用 LangChain、LangGraph 或其他 Agent framework。

## 先运行离线 Smoke Test

```bash
python experiments/week03-minimal-harness/run.py --backend fixture
```

Fixture 会按固定顺序调用 `document_search`、`calculator` 和 `finish`。它用于确认循环、预算与
JSONL trace 可以复现，不代表真实模型能力。

## 使用 Ollama

```bash
ollama pull qwen3-embedding:0.6b
ollama pull qwen3:4b
python experiments/week03-minimal-harness/run.py --backend ollama
```

- `qwen3-embedding:0.6b`：为笔记 chunk 和模型生成的搜索 query 计算 embedding。
- `qwen3:4b`：读取 task、工具 schema 和 Observations，决定下一次 `tool_call` 或 `finish`。

自定义任务：

```bash
python experiments/week03-minimal-harness/run.py \
  --backend ollama \
  --task "查询笔记说明 MCP 与 function calling 的区别，再计算 (18 + 24) / 2"
```

每次运行会把 trace 写入 `runs/week03-minimal-harness/*.jsonl`，该目录不会提交 Git。

## 三个工具

| 工具 | 用途 | 边界 |
| --- | --- | --- |
| `document_search` | 复用第二周 exact-vector RAG index | 只读，最多返回 8 个 chunk |
| `calculator` | 无 `eval` 的 AST 算术计算 | 只允许有限运算符和有限数值 |
| `python_runner` | 纯计算与 assertion | 禁止 import、attribute、文件/网络访问并设置 timeout |

`python_runner` 是教学用受限执行器，不是 OS 级安全 sandbox。

## 谁控制什么

模型可以决定：

- 下一步选哪个已暴露工具。
- 为工具提出哪些参数。
- 何时申请 `finish`。

Harness 决定：

- 模型能看到哪些工具。
- 动作 JSON 和工具参数是否合法。
- 工具是否在 allowlist 中。
- 何时实际执行工具。
- 哪些错误允许自动 retry。
- 步数、模型调用、工具调用、token、成本和时间上限。
- 最终状态是 `success`、`failure` 还是 `budget_exhausted`。

## Retry 规则

- `RetryableModelError` 和 `RetryableToolError`：执行有上限的 exponential backoff。
- JSON/schema 或参数错误：写为错误 Observation，交给模型改变下一步动作。
- 权限和预算错误：不盲目重试。

有副作用的工具尚未加入。后续加入时，retry 前必须实现 idempotency key 或去重机制。

## 建议阅读代码顺序

1. `src/verifiable_agent_lab/harness/loop.py`
2. `src/verifiable_agent_lab/harness/types.py`
3. `src/verifiable_agent_lab/harness/schema.py`
4. `src/verifiable_agent_lab/harness/tools.py`
5. `src/verifiable_agent_lab/harness/events.py`
6. `src/verifiable_agent_lab/harness/backends.py`
7. `experiments/week03-minimal-harness/run.py`

配套阅读：[Tool Use、Function Calling、MCP、Sandbox 与 Retry](../../docs/readings/week03-tool-use-and-harness.zh-CN.md)。

## 当前限制

- 只有当前进程内的单次 run；跨进程 session 恢复属于第四周。
- Context view 只保留最近 Observations，尚未实现 compaction 或 structured handoff。
- 没有交互式 approval UI，目前权限由启动时的 tool allowlist 决定。
- Ollama 的 JSON Schema 只是生成约束；安全仍依赖本地校验和执行边界。

## 已观察到的失败案例

使用本地 `qwen3:4b-instruct` 测试时，最初的通用 action schema 只规定 `arguments` 是 object，
模型把参数错误包装为 `{"tool": ..., "input": ...}`。把每个工具的 `input_schema` 直接嵌入
action schema 后，参数调用恢复正确。随后模型仍可能重复完全相同的成功检索；prompt 会提醒它使用
已有 Observation，而 `max_steps` 仍是阻止无限循环的确定性兜底。
