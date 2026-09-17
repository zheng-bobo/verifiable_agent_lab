# Learning and Build Plan

[English](learning-plan.md) | [简体中文](learning-plan.zh-CN.md)

## Direction

LLM Agent engineering + reinforcement learning + long-running harnesses + verifiable rewards +
reliable evaluation.

## Phase 1: Foundations (Weeks 0–3)

- Review tokenization, Transformer inference, sampling, MDPs and Bellman equations.
- Implement tabular Q-learning and REINFORCE on small environments.
- Build RAG and tool-calling components without an agent framework.
- Produce structured traces for every agent run.
- In Week 3, build a minimal event-driven harness with explicit budgets and terminal states.

## Phase 2: Agent and Policy Learning (Weeks 4–6)

- Compare ReAct and plan-and-execute scaffolds.
- Implement Actor-Critic, PPO clipping and GAE on a toy environment.
- Collect successful and failed agent trajectories.
- Define deterministic rewards and inspect reward-hacking cases.
- In Weeks 4–5, add durable sessions, restart recovery, context compaction/reset, and versioned memory.
- In Week 6, reproduce the same task with the OpenHands Software Agent SDK.

## Phase 3: Evaluation and Alignment (Weeks 7–9)

- Build a 30–100 item benchmark with explicit environments and scorers.
- Compare deterministic graders, LLM-as-judge and voting methods.
- Report pass@1, pass@k, pass^k, cost, latency, false positives and false negatives.
- Run a small DPO or preference-loss experiment.
- Prepare a focused upstream contribution to Lighteval or OpenHands.
- Inject harness failures and measure recovery rate, lost progress, duplicate effects, and resume cost.

## Phase 4: RLVR and Release (Weeks 10–12)

- Implement and test a small GRPO/RLVR experiment if compute permits.
- Add permission limits, timeouts, step budgets and prompt-injection tests.
- Run ablations for verifier, retry and repeated sampling.
- Compare one-shot, persistent, compacted, and structured-reset harness variants.
- Publish code, benchmark, experiment report, failure analysis and demo video.

## Harness Track and Framework

Read the bilingual [Long-Running Agent Harness Evolution](readings/long-running-agent-harness-evolution.md)
note. The implementation sequence is:

1. Build a minimal harness from scratch so the loop, event model, budgets, and persistence are visible.
2. Use [OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk) as the primary
   open-source framework for conversations, event logs, workspaces, condensers, and recovery.
3. Keep [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) as a secondary
   reference for reproducing the Anthropic architecture.

The key invariant is: **session != context window**. A context may be compacted or reset while the
durable session, workspace state, budgets, and outcome history continue to exist.

## Weekly Definition of Done

Each topic is complete only when it includes:

1. A one-sentence problem statement.
2. The central objective or data flow.
3. A minimal implementation.
4. A deliberately constructed failure case.
5. A note connecting it to LLM agents.
