# Verifiable Agent Lab

[English](README.md) | [简体中文](README.zh-CN.md)

一个围绕 **LLM Agent、可验证奖励、推理时扩展与可靠评测** 的学习和实验仓库。

本项目把以下学习主线整合到一个持续演进的工程中：

- [Stanford CS329Z: Engineering AI Agents](https://cs329z.stanford.edu/)
- [Hands-on Modern RL](https://walkinglabs.github.io/hands-on-modern-rl/preface/introduction)
- [nanochat](https://github.com/karpathy/nanochat) 与小语言模型训练基础
- [Lighteval](https://github.com/huggingface/lighteval)、
  [OpenHands](https://github.com/All-Hands-AI/OpenHands) 等开源项目的评测实践

## 目标

构建一个能够调用工具完成代码或数学任务的最小 Agent，并逐步加入：

- 结构化工具调用和可复现轨迹
- 确定性 verifier 与 LLM-as-judge
- `pass@1`、`pass@k`、`pass^k`、成本和延迟评测
- repeated sampling、majority vote 与 Best-of-N
- DPO、GRPO 或 prompt optimization 小型实验
- 失败分析、reward hacking 检查与安全边界

## 仓库结构

```text
.
├── configs/                   # 实验配置
├── data/
│   ├── raw/                   # 原始数据（默认不提交）
│   └── processed/             # 处理后数据（默认不提交）
├── docs/
│   ├── learning-plan.md       # 英文学习计划
│   └── learning-plan.zh-CN.md # 中文学习计划
├── experiments/               # 可复现实验与结果说明
├── src/verifiable_agent_lab/  # 核心 Python 包
└── tests/                     # 单元测试与回归测试
```

## 快速开始

需要 Python 3.11 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## 当前里程碑

- [ ] 跑通最小环境与 Agent loop
- [ ] 保存结构化 trajectory
- [ ] 建立首批可自动验证任务
- [ ] 实现基础 evaluation metrics
- [ ] 完成 repeated-sampling 基线
- [ ] 提交首个上游开源贡献

## 学习计划

- [12 周整合学习与构建计划](docs/learning-plan.zh-CN.md)

## 阅读笔记

- 第一周：[复合 AI 系统](docs/readings/week01-compound-ai-systems.zh-CN.md)
- 第一周：[四种 Agentic Design Patterns](docs/readings/week01-agentic-design-patterns.zh-CN.md)
- [Long-Running Agent Harness 演进](docs/readings/long-running-agent-harness-evolution.zh-CN.md)
  - [Effective Harnesses for Long-Running Agents](docs/readings/effective-harnesses-for-long-running-agents.zh-CN.md)
  - [Harness Design for Long-Running Application Development](docs/readings/harness-design-long-running-apps.zh-CN.md)
- 第二周：[RAGLite 与最小 RAG 基线](docs/readings/week02-raglite-reference.zh-CN.md)

## 实验

- [第一周：GridWorld、Value Iteration 与 Q-learning](experiments/week01-gridworld/README.zh-CN.md)
- [第二周：最小双语 RAG 与重复采样](experiments/week02-rag-sampling/README.zh-CN.md)
  是参考开源项目 [RAGLite](https://github.com/superlinear-ai/raglite) 架构、从零独立重新实现的最小
  RAG；RAGLite 仅作为架构参照，不是运行时依赖。

## 实验原则

1. 每项实验固定随机种子并保存配置。
2. 先建立 baseline，再一次只修改一个变量。
3. 同时报告任务成功率、成本、延迟和失败类型。
4. 区分模型是否生成正确答案（coverage）与系统是否选中答案（precision）。
5. 所有公开结果必须能够通过仓库中记录的命令复现。
