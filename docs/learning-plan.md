# Learning and Build Plan

## Direction

LLM Agent engineering + reinforcement learning + verifiable rewards + reliable evaluation.

## Phase 1: Foundations (Weeks 0–3)

- Review tokenization, Transformer inference, sampling, MDPs and Bellman equations.
- Implement tabular Q-learning and REINFORCE on small environments.
- Build RAG and tool-calling components without an agent framework.
- Produce structured traces for every agent run.

## Phase 2: Agent and Policy Learning (Weeks 4–6)

- Compare ReAct and plan-and-execute scaffolds.
- Implement Actor-Critic, PPO clipping and GAE on a toy environment.
- Collect successful and failed agent trajectories.
- Define deterministic rewards and inspect reward-hacking cases.

## Phase 3: Evaluation and Alignment (Weeks 7–9)

- Build a 30–100 item benchmark with explicit environments and scorers.
- Compare deterministic graders, LLM-as-judge and voting methods.
- Report pass@1, pass@k, pass^k, cost, latency, false positives and false negatives.
- Run a small DPO or preference-loss experiment.
- Prepare a focused upstream contribution to Lighteval or OpenHands.

## Phase 4: RLVR and Release (Weeks 10–12)

- Implement and test a small GRPO/RLVR experiment if compute permits.
- Add permission limits, timeouts, step budgets and prompt-injection tests.
- Run ablations for verifier, retry and repeated sampling.
- Publish code, benchmark, experiment report, failure analysis and demo video.

## Weekly Definition of Done

Each topic is complete only when it includes:

1. A one-sentence problem statement.
2. The central objective or data flow.
3. A minimal implementation.
4. A deliberately constructed failure case.
5. A note connecting it to LLM agents.

