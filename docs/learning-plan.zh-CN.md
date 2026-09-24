# Verifiable Agent Lab：12 周整合学习与构建计划

[English](learning-plan.md) | [简体中文](learning-plan.zh-CN.md)

## 总方向

本计划围绕一个持续演进的项目，把四条学习线整合起来：

> **LLM 基础（nanochat）→ RL/PPO/GRPO → Agent 与 Long-running Harness → 可验证评测与开源贡献**

主要资料与项目：

- [Stanford CS329Z: Engineering AI Agents](https://cs329z.stanford.edu/)
- [Hands-on Modern RL](https://walkinglabs.github.io/hands-on-modern-rl/preface/introduction)
- [nanochat](https://github.com/karpathy/nanochat)
- [Lighteval](https://github.com/huggingface/lighteval)
- [OpenHands](https://github.com/All-Hands-AI/OpenHands)
- [OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)

第 0 周是正式 12 周开始前的准备周；第 1–12 周是主体计划。

## 最终目标

到第 12 周结束，发布一个能够使用工具解决代码或数学任务的 **Verifiable Agent Lab**，并包含：

- 基础 Agent loop、结构化工具调用与可恢复 session
- 确定性 verifier 与 30–100 条可自动验证任务
- `pass@1`、`pass@k`、`pass^k`、成本和延迟指标
- repeated sampling、majority vote 与 Best-of-N 对比
- 完整 trajectory、失败分类与 reward-hacking 检查
- DPO、GRPO 或 prompt optimization 中至少一个小型实验
- one-shot、持久化、compaction 与 structured reset 的 Harness 消融
- 至少一次面向 Lighteval、OpenHands 或课程项目的上游贡献

优先选择代码或数学任务，因为它们更容易构建确定性 verifier。

## 路线总览

| 周次 | 主题 | 主要产物 |
| --- | --- | --- |
| 第 0 周 | 基础与环境 | 可复现仓库、实验配置、项目问题定义 |
| 第 1 周 | Agent 与 RL 的共同抽象 | GridWorld、Value Iteration、Q-learning |
| 第 2 周 | LLM 推理、RAG 与采样 | 最小 RAG、structured output、`pass@k` 曲线 |
| 第 3 周 | 工具调用、REINFORCE 与最小 Harness | 三工具 Agent loop、JSONL trace、预算控制 |
| 第 4 周 | Agent 模式、Actor-Critic 与恢复 | ReAct/Plan-and-Execute、崩溃恢复 |
| 第 5 周 | 多 Agent、PPO、Context 与 Memory | PPO、Generator–Critic 对比、memory 安全 |
| 第 6 周 | 数据、SFT、RLHF 与 OpenHands SDK | 轨迹数据集、SDK 复现与 trace 对比 |
| 第 7 周 | Benchmark、DPO 与 Harness 评测 | 30–100 条 benchmark、failure injection |
| 第 8 周 | Judge、GRPO 与 Verifier | 三类 evaluator 对比报告 |
| 第 9 周 | Coding Agent 与开源问题 | 真实修复任务、Lighteval/OpenHands 贡献 |
| 第 10 周 | 小型 GRPO/RLVR 与长任务 | Toy/LoRA GRPO、long-running run |
| 第 11 周 | 安全、可观察性与消融 | 权限与预算、Harness 四组对比 |
| 第 12 周 | 发布与复盘 | 报告、演示、失败分析、上游 PR |

## 当前进度（2026-09-24）

- 第 0 周：仓库、Python 包、pytest、Ruff 与实验结构已建立。
- 第 1 周：GridWorld、Value Iteration、Q-learning、三组探索率实验和两篇 CS329Z 阅读笔记已完成；Agent–MDP 独立总结与正式失败分析仍可补充。
- 第 2 周：最小双语 RAG、structured output、1/4/8/16 repeated sampling、`pass@k`、
  selection 与失败案例记录已经完成。
- 第 3 周进行中：三工具最小 Harness、工具白名单、预算、有限 retry、JSONL trace、从零实现的
  NumPy REINFORCE 与 value baseline 对照已经完成；下一步是 Harness 失败案例实验。

---

## 第 0 周：9 月 17–22 日——整理基础与环境

### 学习

- 回顾 nanochat 中 tokenizer、Transformer forward、交叉熵和采样流程。
- Hands-on Modern RL：预备知识、2.1–2.3，以及必要时的附录 D.2。

### 实践

- 跑通 CartPole。
- 建立统一 GitHub 仓库。
- 配置 pytest、Ruff、日志、随机种子和实验配置。
- 写一页项目问题定义：输入、环境、动作、奖励和评测指标。

### 验收

- 能用自己的话解释 state、action、policy、reward 与 return。
- 仓库具有可复现的安装、测试和实验命令。
- 暂时不训练大模型。

---

## 第 1 周：9 月 23–27 日——Agent 与 RL 的共同抽象

### CS329Z

- Agentic systems 与 compound AI systems。
- Decomposition、data 与 evaluation。

### Modern RL

- 3.1–3.3：价值函数、Bellman 方程、Value Iteration 与 Q-learning。
- 4.1：动态规划、Monte Carlo 与 TD。

### 实践

- 从零实现 GridWorld。
- 实现 Value Iteration 与表格型 Q-learning。
- 比较 `epsilon = 0.01 / 0.1 / 0.3`。
- 将 GridWorld 映射到 LLM Agent：state、action、environment、reward、trajectory 与预算。

### 产物与验收

- 可复现的 GridWorld 实验与单元测试。
- 一篇《Agent loop 和 MDP 哪里相同、哪里不同》的双语短笔记。
- 能解释 Value Iteration 与 Q-learning 的信息前提，以及现实 Agent 为什么更接近 POMDP。

---

## 第 2 周：9 月 28 日–10 月 4 日——LLM 推理、RAG 与采样

### CS329Z

- LLM API、structured output、decoding 与 test-time compute。
- RAG、embedding、chunking 与 retrieval。

### Modern RL

- 4.2：策略采样与数据来源。
- 4.3：奖励函数设计。
- 附录 B.7：采样方法。

### 实践

- 不使用 Agent 框架，从零构建最小 RAG pipeline。
- 使用项目中的双语笔记作为小型知识库。
- 给模型加入 JSON Schema 输出校验。
- 对同一个问题分别采样 `1、4、8、16` 次。
- 记录成功率、token、延迟、成本、输出多样性和检索命中情况。

### 产物与验收

- 第一份 evaluation notebook 或可复现脚本。
- `pass@k` 随采样数变化的曲线。
- 至少一个检索失败、错误 chunk 或 schema 不合法的失败案例。
- 能区分 coverage、selection precision 与最终系统正确率。

---

## 第 3 周：10 月 5–11 日——工具调用、策略梯度与最小 Harness

### CS329Z

- Tool use、function calling、MCP、sandbox 与 retry。
- Agent framework 与 orchestration。
- 开始 CS329Z HW1 与项目 proposal。

### Modern RL

- 6.1–6.3：策略梯度与 REINFORCE。
- 6.4–6.6：CartPole 与 value baseline。
- 附录 D.3.2：策略梯度推导。

### Agent 与 Harness 实践

- 不使用 LangChain，手写 `observe → decide → act → observe → stop` Agent loop。
- 只提供三个工具：calculator、受限 Python/test runner、document search。
- 使用结构化 action/observation event 和 JSONL event log。
- 加入步数、token、时间和成本预算，以及明确的成功、失败和耗尽状态。
- 从零实现 REINFORCE，再加入 baseline。

### 验收

- 能解释 baseline 为什么不改变期望梯度，却能降低方差。
- 每次 Agent 运行都产生结构化、可回放的 trace。
- 权限、参数校验、预算与终止条件由 Harness 而不是模型控制。

---

## 第 4 周：10 月 12–18 日——Agent 模式、Actor-Critic 与 Session 恢复

### CS329Z

- ReAct、plan-and-execute、reflection。
- Memory 与 multi-agent 基础。

### Modern RL

- 7.1–7.4：advantage、Actor-Critic 与 critic 训练。

### 实践

- 为同一组任务实现 ReAct 与 plan-and-execute。
- 实现基础 Actor-Critic。
- 为每次逻辑运行分配 session ID，并持久化 append-only event log。
- 在工具调用后主动终止进程，再从持久化事件恢复。
- 让具有副作用的工具支持 idempotency key，避免 replay 重复执行。

### 产物与验收

- 两种 Agent 的失败类型对比表。
- 至少 20 条成功或失败的完整执行轨迹。
- 进程重启后能够恢复，且不会丢失已确认进度或重复副作用。

---

## 第 5 周：10 月 19–25 日——多 Agent、PPO、Context 与 Memory

### CS329Z

- 单 Agent 与多 Agent。
- Prompt optimization、fine-tuning、test-time compute、RLHF 与 DPO。

### Modern RL

- 8.1–8.4：PPO、clip objective、GAE 与数学推导。
- 附录 B.2 与 D.3.3。

### 实践

- 从零实现简化 PPO，并在 CartPole 上验证。
- 比较 single agent、generator + critic、generator + critic + retry。
- 保留完整 event log，同时实现滚动 context view。
- 比较 truncation、compaction 与 structured reset/handoff。
- 分离只读 reference memory 与可写 session memory，并记录版本和来源。
- 构造 memory-poisoning 输入，验证其不能静默修改可信指令。

### 验收

- 能解释 importance ratio、PPO clipping 与 GAE 的 bias–variance trade-off。
- 能说明 Context Window、Session、Memory Store 与 Workspace 的不同生命周期。
- 能解释为什么 LLM judge 的分数不等于可靠 reward。

---

## 第 6 周：10 月 26 日–11 月 1 日——数据、SFT、RLHF 与 OpenHands SDK

### CS329Z

- Agent traces、demonstrations、feedback、数据飞轮与 synthetic data。
- HW2 发布。

### Modern RL

- 13.1–13.7：RLHF、SFT、AI feedback、reward hacking 与 alignment evaluation。
- 13.9：PPO-RLHF 训练循环；暂不运行 13.8 的大型实验。

### 实践

- 从 Agent trace 整理成功轨迹、失败轨迹、人工偏好对与 verifier 分数。
- 定义统一数据 schema，并检测空输出、超长轨迹和异常奖励。
- 使用 OpenHands Software Agent SDK 重建第 3 周的双工具任务。
- 使用 `Agent`、`Conversation`、EventLog、Workspace 与 Condenser。
- 暂停、保存并恢复 Conversation，比较 SDK trace 与手写 JSONL trace。

### 开源动作

- 阅读 Lighteval 贡献指南与测试结构。
- 选择一个 metric、task 或 reproducibility issue，并先提交可复现信息。

---

## 第 7 周：11 月 2–8 日——Benchmark、DPO 与 Harness 评测

### CS329Z

- 数据筛选与质量。
- Evaluation 4-tuple：request、environment、stopping criteria、scorer。
- Midpoint demo。

### Modern RL

- 14.1–14.4：DPO；只做小模型或 toy verification。

### 实践

- 建立 30–100 条 tiny benchmark。
- 每条任务包含输入、环境状态、最大步数和确定性 scorer。
- 用成功/失败轨迹构造偏好对，运行小型 LoRA-DPO 或验证 DPO loss。
- 注入进程在 action 与 observation 之间终止、工具 timeout 和畸形输出等故障。
- 测量 verified task success、恢复率、恢复开销和丢失进度。

### 产物

- Midpoint demo、benchmark 数据卡与失败分类初版。

---

## 第 8 周：11 月 9–15 日——LLM-as-Judge、GRPO 与 Verifier

### CS329Z

- Code grader、LLM-as-judge、`pass@k`、`pass^k`、judge bias 与 prompt injection。

### Modern RL

- 15.1–15.5：GRPO、R1-Zero、RLVR reward、环境与 verifier。
- 17.1、17.4、17.6：结果奖励、形式化 verifier、并行推理与答案汇总。

### 实践

比较三类 evaluator：

1. 确定性测试或规则 verifier。
2. LLM-as-judge。
3. Majority vote 或 Best-of-N。

记录 false positive、false negative、人工一致率、采样饱和点、成本与延迟。同时注入错误 verifier、
损坏 handoff、未完成任务时的 context reset 和可写 memory 污染。

### 产物

- 一份 evaluator 对比实验报告；这是整个项目的核心报告之一。

---

## 第 9 周：11 月 16–22 日——Coding Agent 与真实开源问题

### CS329Z

- Coding agents、SWE-agent、OpenHands 与 SWE-bench。
- HW2 截止。

### Modern RL

- 16.1–16.3：推理模型、R1-Zero 与 test-time scaling。
- 19.1–19.5：Agentic RL、多轮交互、轨迹信用分配与工具调用。
- 20.1：SWE-RL 基础。

### 实践

- 从一个小型 Python 仓库构造 10–20 个真实修复任务。
- 让 Agent 定位文件、修改代码、运行测试并根据错误重试。
- 记录 resolve rate、`pass@k`、工具调用次数、token 成本和错误恢复率。
- 继续测试重复副作用、并发/过期状态与 context 信息损失。

### 开源动作

- 向 Lighteval 提交首个窄范围 PR，优先选择测试、metric edge case 或文档与实现不一致。
- 没有合适问题时，转向 OpenHands evaluation 或 Software Agent SDK。

---

## 第 10 周：11 月 23–29 日——小型 GRPO/RLVR 与 Long-running Run

### Modern RL

- 15.3–15.4：RLVR reward 与 GRPO 改进。
- 25.1、25.2、25.4、25.5：reward hacking、假性收益与评测协议。

### 算力有限路线

- 在 toy policy 或极小语言模型上实现 GRPO loss。
- 测试 group reward、advantage normalization 与 KL。
- 人工构造 reward-hacking 样本。

### 有 GPU 路线

- 选择 0.5B–1.5B 模型进行少量数学或格式化工具调用任务的 LoRA-GRPO。
- 关注 KL、reward variance、训练稳定性和真实验证率，而不是追求分数。

### Harness 实践

- 启动一个跨多 session 的长任务，确保会触发 compaction 或 structured reset。
- 保存完整 event timeline、checkpoint、恢复证据与资源指标。

---

## 第 11 周：11 月 30 日–12 月 6 日——安全、可观察性与最终消融

### CS329Z

- Proactive agents、隐私、信任、生产可观察性与 long-running systems。

### Modern RL

- 19.2–19.7：多轮 RL、信用分配、搜索增强与代码解释器。
- 附录 A：训练调试、轨迹与沙箱。

### 实践

- 加入最大步数、工具权限、超时、token/cost budget、prompt-injection 测试和完整 tracing。
- 完成 verifier 消融：无 verifier、有 verifier、verifier + retry、verifier + repeated sampling。
- 完成 Harness 消融：
  1. One-shot agent
  2. 无 compaction 的持久化 session
  3. 带 compaction 的持久化 session
  4. 带 structured reset/handoff 的持久化 session

### 验收

- 至少一个 Harness 设计决策由测量结果支持，而不是凭直觉选择。

---

## 第 12 周：12 月 7–13 日——发布与复盘

### 最终交付物

- 完整的中英文 GitHub README 与运行说明。
- 训练和评测配置。
- 30–100 条 benchmark 与数据卡。
- 指标表、曲线和 Harness event timeline。
- 至少 10 个典型失败案例及修复或缓解方案。
- Context、Session、Memory 与 Workspace 的架构说明。
- 5–10 分钟英文演示视频。
- 中英文技术文章，或中文正文加英文摘要。
- 一个已经提交的开源 PR；收到 maintainer review 也算阶段成功。

### 最终结论必须回答

- 哪些系统改进真正提高了 verified task success？
- 哪些 Agent loop 只增加了成本和错误传播？
- Repeated sampling 提高的是 coverage，还是最终选择质量？
- 哪种 context 策略在当前模型和任务上最好？
- Verifier 在哪些情况下被利用、误判或失效？

---

## 每周时间分配

以每周 12 小时为基准：

| 模块 | 时间 |
| --- | ---: |
| CS329Z 讲义与阅读 | 3 小时 |
| Modern RL 理论 | 3 小时 |
| 算法实现与实验 | 3 小时 |
| Agent/Harness 主项目 | 2 小时 |
| 记录与开源交流 | 1 小时 |

如果每周只有 8 小时，保留 CS329Z、RL 主干、最小实现和主项目各 2 小时；删除额外论文和选修章节，
不要删除实践。

## 第一轮暂时跳过

- DQN 的高级变体与 Atari。
- AlphaGo 完整复现。
- DDPG、TD3 与 SAC 的深入实现。
- 离线 RL、逆 RL、元 RL 与多模态 RL。
- 大规模分布式训练工程。
- 缺少确定性 verifier 的大型开放式任务。

## 每周统一完成标准

每个主题只有在包含以下内容后才算完成：

1. 用一句话说明要解决的问题。
2. 写出核心目标函数或数据流。
3. 完成一个可运行的最小实现。
4. 构造并解释一个必然失败的案例。
5. 说明该主题与 LLM Agent 的联系。
6. 固定随机种子，并保存配置、原始结果与复现命令。
7. 测试和静态检查通过，中英文文档保持同步。

Harness 主线额外要求：**Session != Context Window**。Context 可以被压缩或重置，但持久化
session、workspace、预算、event history 和 outcome 不应因此消失。
