# 学习与构建计划

[English](learning-plan.md) | [简体中文](learning-plan.zh-CN.md)

## 方向

LLM Agent 工程 + 强化学习 + 可验证奖励 + 可靠评测。

## 第一阶段：基础（第 0–3 周）

- 回顾 tokenizer、Transformer 推理、采样、MDP 与贝尔曼方程。
- 在小型环境中实现表格型 Q-learning 和 REINFORCE。
- 不依赖 Agent 框架，从零构建 RAG 和工具调用组件。
- 为每次 Agent 执行生成结构化轨迹。

## 第二阶段：Agent 与策略学习（第 4–6 周）

- 比较 ReAct 与 plan-and-execute scaffold。
- 在玩具环境中实现 Actor-Critic、PPO clipping 和 GAE。
- 收集 Agent 的成功与失败轨迹。
- 定义确定性奖励，并检查 reward hacking 案例。

## 第三阶段：评测与对齐（第 7–9 周）

- 构建包含 30–100 个任务的 benchmark，明确环境与 scorer。
- 比较确定性 grader、LLM-as-judge 和投票方法。
- 报告 pass@1、pass@k、pass^k、成本、延迟、假阳性和假阴性。
- 运行一个小型 DPO 或偏好损失实验。
- 准备一次面向 Lighteval 或 OpenHands 的聚焦式上游贡献。

## 第四阶段：RLVR 与发布（第 10–12 周）

- 算力允许时，实现并测试一个小型 GRPO/RLVR 实验。
- 加入权限限制、超时、步数预算和 prompt injection 测试。
- 对 verifier、retry 和 repeated sampling 进行消融实验。
- 发布代码、benchmark、实验报告、失败分析和演示视频。

## 每周完成标准

每个主题只有在包含以下内容后才算完成：

1. 用一句话说明要解决的问题。
2. 写出核心目标函数或数据流。
3. 完成一个最小实现。
4. 构造一个必然失败的案例。
5. 说明该主题与 LLM Agent 的联系。

