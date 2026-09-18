# Verifiable Agent Lab: 12-Week Integrated Learning and Build Plan

[English](learning-plan.md) | [简体中文](learning-plan.zh-CN.md)

## Direction

This plan connects four learning tracks through one evolving project:

> **LLM foundations (nanochat) → RL/PPO/GRPO → agents and long-running harnesses → verifiable evaluation and open-source contribution**

Primary resources and projects:

- [Stanford CS329Z: Engineering AI Agents](https://cs329z.stanford.edu/)
- [Hands-on Modern RL](https://walkinglabs.github.io/hands-on-modern-rl/preface/introduction)
- [nanochat](https://github.com/karpathy/nanochat)
- [Lighteval](https://github.com/huggingface/lighteval)
- [OpenHands](https://github.com/All-Hands-AI/OpenHands)
- [OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)

Week 0 is preparation before the main program; Weeks 1–12 are the core twelve-week plan.

## Final Goal

By the end of Week 12, publish a **Verifiable Agent Lab** that can use tools to solve coding or
mathematics tasks and includes:

- A basic agent loop, structured tool calls, and recoverable sessions
- Deterministic verifiers and a 30–100 item automatically verifiable task set
- `pass@1`, `pass@k`, `pass^k`, cost, and latency metrics
- Repeated-sampling, majority-vote, and Best-of-N comparisons
- Complete trajectories, failure categories, and reward-hacking checks
- At least one small DPO, GRPO, or prompt-optimization experiment
- Harness ablations across one-shot, persistence, compaction, and structured reset
- At least one upstream contribution to Lighteval, OpenHands, or a course project

Coding or mathematics tasks are preferred because they support deterministic verifiers.

## Roadmap

| Week | Theme | Main deliverable |
| --- | --- | --- |
| Week 0 | Foundations and environment | Reproducible repository, experiment config, project definition |
| Week 1 | Shared abstraction of agents and RL | GridWorld, value iteration, Q-learning |
| Week 2 | LLM inference, RAG, and sampling | Minimal RAG, structured output, `pass@k` curve |
| Week 3 | Tool use, REINFORCE, and minimal harness | Three-tool loop, JSONL traces, budget control |
| Week 4 | Agent patterns, Actor-Critic, and recovery | ReAct/Plan-and-Execute, crash recovery |
| Week 5 | Multi-agent, PPO, context, and memory | PPO, Generator–Critic comparison, memory safety |
| Week 6 | Data, SFT, RLHF, and OpenHands SDK | Trace dataset, SDK reproduction, trace comparison |
| Week 7 | Benchmark, DPO, and harness evaluation | 30–100 tasks and failure injection |
| Week 8 | Judges, GRPO, and verifiers | Three-way evaluator comparison report |
| Week 9 | Coding agents and real open-source issues | Repair tasks and Lighteval/OpenHands contribution |
| Week 10 | Small GRPO/RLVR and a long run | Toy/LoRA GRPO and a multi-session run |
| Week 11 | Safety, observability, and ablation | Permissions, budgets, four harness variants |
| Week 12 | Release and retrospective | Report, demo, failure analysis, upstream PR |

## Current Progress — September 18, 2026

- Week 0: the repository, Python package, pytest, Ruff, and experiment structure exist.
- Week 1: GridWorld, value iteration, Q-learning, three exploration-rate experiments, and two CS329Z reading notes are complete; a standalone Agent–MDP note and formal failure analysis remain optional follow-ups.
- Next: Week 2's minimal RAG and repeated-sampling evaluation.

---

## Week 0: September 17–22 — Foundations and Environment

### Study

- Review tokenization, the Transformer forward pass, cross-entropy, and sampling in nanochat.
- Hands-on Modern RL prerequisites, Sections 2.1–2.3, and Appendix D.2 as needed.

### Build

- Run CartPole.
- Create a unified GitHub repository.
- Configure pytest, Ruff, logging, random seeds, and experiment configuration.
- Write a one-page project definition covering inputs, environment, actions, rewards, and metrics.

### Acceptance

- Explain state, action, policy, reward, and return in your own words.
- Provide reproducible install, test, and experiment commands.
- Do not begin large-model training yet.

---

## Week 1: September 23–27 — The Shared Abstraction of Agents and RL

### CS329Z

- Agentic systems and compound AI systems.
- Decomposition, data, and evaluation.

### Modern RL

- Sections 3.1–3.3: value functions, Bellman equations, value iteration, and Q-learning.
- Section 4.1: dynamic programming, Monte Carlo, and temporal difference learning.

### Build

- Implement GridWorld from scratch.
- Implement value iteration and tabular Q-learning.
- Compare `epsilon = 0.01 / 0.1 / 0.3`.
- Map GridWorld to an LLM agent: state, action, environment, reward, trajectory, and budget.

### Deliverables and Acceptance

- A reproducible GridWorld experiment with unit tests.
- A bilingual note on where an agent loop and an MDP are similar and where they differ.
- Explain the information assumptions behind value iteration and Q-learning, and why a real agent is
  often better modeled as a POMDP.

---

## Week 2: September 28–October 4 — LLM Inference, RAG, and Sampling

### CS329Z

- LLM APIs, structured output, decoding, and test-time compute.
- RAG, embeddings, chunking, and retrieval.

### Modern RL

- Section 4.2: policy sampling and data sources.
- Section 4.3: reward design.
- Appendix B.7: sampling methods.

### Build

- Build a minimal RAG pipeline without an agent framework.
- Use the project's bilingual notes as a small knowledge base.
- Validate model responses against a JSON Schema.
- Sample the same question `1, 4, 8, 16` times.
- Record success, tokens, latency, cost, output diversity, and retrieval hits.

### Deliverables and Acceptance

- A first evaluation notebook or reproducible script.
- A curve showing `pass@k` against the number of samples.
- At least one retrieval, chunking, or schema-validation failure case.
- Explain coverage, selection precision, and final system accuracy separately.

---

## Week 3: October 5–11 — Tool Use, Policy Gradients, and a Minimal Harness

### CS329Z

- Tool use, function calling, MCP, sandboxing, and retries.
- Agent frameworks and orchestration.
- Begin CS329Z HW1 and the project proposal.

### Modern RL

- Sections 6.1–6.3: policy gradients and REINFORCE.
- Sections 6.4–6.6: CartPole and a value baseline.
- Appendix D.3.2: policy-gradient derivation.

### Agent and Harness Build

- Hand-write an `observe → decide → act → observe → stop` loop without LangChain.
- Expose only a calculator, a restricted Python/test runner, and document search.
- Use structured action/observation events and a JSONL event log.
- Add step, token, time, and cost budgets with explicit success, failure, and exhaustion states.
- Implement REINFORCE from scratch, then add a baseline.

### Acceptance

- Explain why a baseline reduces variance without changing the expected gradient.
- Produce a structured, replayable trace for every agent run.
- Keep permissions, validation, budgets, and terminal conditions under harness control.

---

## Week 4: October 12–18 — Agent Patterns, Actor-Critic, and Session Recovery

### CS329Z

- ReAct, plan-and-execute, reflection, memory, and multi-agent foundations.

### Modern RL

- Sections 7.1–7.4: advantage, Actor-Critic, and critic training.

### Build

- Implement ReAct and plan-and-execute over the same task set.
- Implement a basic Actor-Critic method.
- Give each logical run a session ID and persist an append-only event log.
- Kill the process after a tool call and recover from durable events.
- Add idempotency keys to side-effecting tools so replay cannot duplicate effects.

### Deliverables and Acceptance

- A failure comparison for the two agent patterns.
- At least 20 complete successful or failed trajectories.
- Recovery after process restart without losing committed progress or repeating side effects.

---

## Week 5: October 19–25 — Multi-Agent Systems, PPO, Context, and Memory

### CS329Z

- Single-agent versus multi-agent systems.
- Prompt optimization, fine-tuning, test-time compute, RLHF, and DPO.

### Modern RL

- Sections 8.1–8.4: PPO, the clipped objective, GAE, and derivations.
- Appendices B.2 and D.3.3.

### Build

- Implement simplified PPO and verify it on CartPole.
- Compare a single agent, generator + critic, and generator + critic + retry.
- Retain the full event log while constructing a rolling context view.
- Compare truncation, compaction, and structured reset/handoff.
- Separate read-only reference memory from writable session memory, recording version and provenance.
- Test a memory-poisoning input that must not silently modify trusted instructions.

### Acceptance

- Explain the importance ratio, PPO clipping, and GAE's bias–variance trade-off.
- Distinguish the lifecycles of a context window, session, memory store, and workspace.
- Explain why an LLM judge score is not automatically a reliable reward.

---

## Week 6: October 26–November 1 — Data, SFT, RLHF, and OpenHands SDK

### CS329Z

- Agent traces, demonstrations, feedback, data flywheels, and synthetic data.
- HW2 release.

### Modern RL

- Sections 13.1–13.7: RLHF, SFT, AI feedback, reward hacking, and alignment evaluation.
- Section 13.9: the PPO-RLHF loop; skip the large Section 13.8 experiment.

### Build

- Organize successful traces, failed traces, human preference pairs, and verifier scores.
- Define one data schema and detect empty output, overlong traces, and abnormal rewards.
- Rebuild Week 3's two-tool task with the OpenHands Software Agent SDK.
- Use `Agent`, `Conversation`, EventLog, Workspace, and a Condenser.
- Pause, persist, and resume a Conversation; compare the SDK trace with the handwritten JSONL trace.

### Open-Source Action

- Read Lighteval's contribution guide and tests.
- Select a metric, task, or reproducibility issue and first post reproducible evidence.

---

## Week 7: November 2–8 — Benchmarking, DPO, and Harness Evaluation

### CS329Z

- Data selection and quality.
- The evaluation four-tuple: request, environment, stopping criteria, and scorer.
- Midpoint demo.

### Modern RL

- Sections 14.1–14.4: DPO on a small model or as a toy loss verification.

### Build

- Create a 30–100 item benchmark.
- Give every task an input, environment state, step limit, and deterministic scorer.
- Construct preferences from successful and failed traces; run small LoRA-DPO or verify DPO loss.
- Inject process termination between action and observation, tool timeout, and malformed tool output.
- Measure verified success, recovery rate, recovery overhead, and lost progress.

### Deliverables

- Midpoint demo, benchmark data card, and initial failure taxonomy.

---

## Week 8: November 9–15 — LLM-as-Judge, GRPO, and Verifiers

### CS329Z

- Code graders, LLM-as-judge, `pass@k`, `pass^k`, judge bias, and prompt injection.

### Modern RL

- Sections 15.1–15.5: GRPO, R1-Zero, RLVR reward, environments, and verifiers.
- Sections 17.1, 17.4, and 17.6: outcome reward, formal verifiers, parallel inference, and aggregation.

### Build

Compare three evaluator types:

1. Deterministic tests or rule-based verifiers.
2. LLM-as-judge.
3. Majority vote or Best-of-N.

Record false positives, false negatives, human agreement, sampling saturation, cost, and latency.
Also inject an incorrect verifier, corrupted handoff, premature context reset, and writable-memory
poisoning.

### Deliverable

- An evaluator comparison report; this is one of the project's central reports.

---

## Week 9: November 16–22 — Coding Agents and Real Open-Source Issues

### CS329Z

- Coding agents, SWE-agent, OpenHands, and SWE-bench.
- HW2 deadline.

### Modern RL

- Sections 16.1–16.3: reasoning models, R1-Zero, and test-time scaling.
- Sections 19.1–19.5: agentic RL, multi-turn interaction, credit assignment, and tool use.
- Section 20.1: SWE-RL foundations.

### Build

- Construct 10–20 realistic repair tasks from a small Python repository.
- Ask the agent to locate files, edit code, run tests, and retry from failures.
- Record resolve rate, `pass@k`, tool calls, token cost, and recovery rate.
- Continue testing duplicate effects, stale or concurrent state, and context-information loss.

### Open-Source Action

- Submit a narrow Lighteval PR, preferably a test, metric edge case, or documentation mismatch.
- If none fits, contribute to OpenHands evaluation or the Software Agent SDK.

---

## Week 10: November 23–29 — Small GRPO/RLVR and a Long-Running Run

### Modern RL

- Sections 15.3–15.4: RLVR reward and GRPO improvements.
- Sections 25.1, 25.2, 25.4, and 25.5: reward hacking, spurious gains, and evaluation protocol.

### Limited-Compute Route

- Implement GRPO loss for a toy policy or tiny language model.
- Test group reward, advantage normalization, and KL behavior.
- Construct reward-hacking examples manually.

### GPU Route

- Use a 0.5B–1.5B model for a small LoRA-GRPO run on mathematics or formatted tool calls.
- Focus on KL, reward variance, stability, and true verification rate rather than headline score.

### Harness Build

- Start a multi-session task long enough to trigger compaction or structured reset.
- Save its complete event timeline, checkpoints, recovery evidence, and resource metrics.

---

## Week 11: November 30–December 6 — Safety, Observability, and Final Ablations

### CS329Z

- Proactive agents, privacy, trust, production observability, and long-running systems.

### Modern RL

- Sections 19.2–19.7: multi-turn RL, credit assignment, search augmentation, and code interpreters.
- Appendix A: debugging, trajectories, and sandboxes.

### Build

- Add step limits, tool permissions, timeouts, token/cost budgets, prompt-injection tests, and tracing.
- Compare no verifier, verifier, verifier + retry, and verifier + repeated sampling.
- Compare four harness variants:
  1. One-shot agent
  2. Persistent session without compaction
  3. Persistent session with compaction
  4. Persistent session with structured reset/handoff

### Acceptance

- Support at least one harness design decision with measurements rather than intuition.

---

## Week 12: December 7–13 — Release and Retrospective

### Final Deliverables

- Complete bilingual GitHub README and run instructions.
- Training and evaluation configurations.
- A 30–100 item benchmark with a data card.
- Metric tables, curves, and the harness event timeline.
- At least ten representative failures with fixes or mitigations.
- An architecture explanation for context, session, memory, and workspace.
- A five-to-ten-minute English demo video.
- Bilingual technical articles, or a Chinese article with an English abstract.
- One submitted upstream PR; maintainer review also counts as stage success.

### Final Questions

- Which system changes actually improved verified task success?
- Which agent loops only added cost and error propagation?
- Did repeated sampling improve coverage or final selection quality?
- Which context strategy worked best for the current model and task?
- When did the verifier get exploited, misclassify, or fail?

---

## Weekly Time Budget

Assuming twelve hours per week:

| Track | Time |
| --- | ---: |
| CS329Z lectures and reading | 3 hours |
| Modern RL theory | 3 hours |
| Algorithms and experiments | 3 hours |
| Agent/harness project | 2 hours |
| Documentation and open-source communication | 1 hour |

With only eight hours, keep two hours each for CS329Z, core RL, implementation, and the main project.
Drop optional papers and elective chapters, not hands-on work.

## Deferred in the First Pass

- Advanced DQN variants and Atari.
- A full AlphaGo reproduction.
- Deep implementations of DDPG, TD3, and SAC.
- Offline, inverse, meta, and multimodal RL.
- Large-scale distributed training infrastructure.
- Large open-ended tasks without deterministic verifiers.

## Weekly Definition of Done

A topic is complete only when it includes:

1. A one-sentence problem statement.
2. The central objective or data flow.
3. A runnable minimal implementation.
4. A deliberately constructed and explained failure case.
5. A note connecting the topic to LLM agents.
6. Fixed seeds plus saved configuration, raw results, and reproduction commands.
7. Passing tests and static checks with synchronized English and Chinese documentation.

The harness track has one additional invariant: **session != context window**. Context may be
compacted or reset, but the durable session, workspace, budgets, event history, and outcome must not
disappear with it.
