# Verifiable Agent Lab

[English](README.md) | [简体中文](README.zh-CN.md)

A learning and experimentation repository focused on **LLM agents, verifiable rewards,
inference-time scaling, and reliable evaluation**.

The project brings the following learning tracks together in one evolving codebase:

- [Stanford CS329Z: Engineering AI Agents](https://cs329z.stanford.edu/)
- [Hands-on Modern RL](https://walkinglabs.github.io/hands-on-modern-rl/preface/introduction)
- [nanochat](https://github.com/karpathy/nanochat) and small-language-model training fundamentals
- Evaluation practice with open-source projects such as
  [Lighteval](https://github.com/huggingface/lighteval) and
  [OpenHands](https://github.com/All-Hands-AI/OpenHands)

## Goals

Build a minimal agent that can use tools to solve coding or mathematics tasks, then gradually add:

- Structured tool calls and reproducible trajectories
- Deterministic verifiers and LLM-as-judge evaluation
- `pass@1`, `pass@k`, `pass^k`, cost, and latency metrics
- Repeated sampling, majority voting, and Best-of-N selection
- Small DPO, GRPO, or prompt-optimization experiments
- Failure analysis, reward-hacking checks, and safety boundaries

## Repository Structure

```text
.
├── configs/                   # Experiment configurations
├── data/
│   ├── raw/                   # Raw data (not committed by default)
│   └── processed/             # Processed data (not committed by default)
├── docs/
│   ├── learning-plan.md       # Learning plan in English
│   └── learning-plan.zh-CN.md # Chinese translation
├── experiments/               # Reproducible experiments and result notes
├── src/verifiable_agent_lab/  # Core Python package
└── tests/                     # Unit and regression tests
```

## Quick Start

Python 3.11 or later is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## Current Milestones

- [ ] Run a minimal environment and agent loop
- [ ] Save structured trajectories
- [ ] Create the first automatically verifiable tasks
- [ ] Implement baseline evaluation metrics
- [ ] Complete a repeated-sampling baseline
- [ ] Submit the first upstream open-source contribution

## Learning Plan

- [12-Week Integrated Learning and Build Plan](docs/learning-plan.md)

## Reading Notes

- Week 1: [Compound AI Systems](docs/readings/week01-compound-ai-systems.md)
- Week 1: [Four Agentic Design Patterns](docs/readings/week01-agentic-design-patterns.md)
- [Long-Running Agent Harness Evolution](docs/readings/long-running-agent-harness-evolution.md)
  - [Effective Harnesses for Long-Running Agents](docs/readings/effective-harnesses-for-long-running-agents.md)
  - [Harness Design for Long-Running Application Development](docs/readings/harness-design-long-running-apps.md)

## Experiments

- [Week 1: GridWorld with Value Iteration and Q-learning](experiments/week01-gridworld/README.md)

## Experiment Principles

1. Fix random seeds and save the configuration for every experiment.
2. Establish a baseline before changing one variable at a time.
3. Report task success, cost, latency, and failure categories together.
4. Distinguish coverage—the model generated a correct answer—from precision—the system selected it.
5. Ensure every published result can be reproduced with commands documented in the repository.
