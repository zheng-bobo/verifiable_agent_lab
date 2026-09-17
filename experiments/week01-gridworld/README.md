# Week 01: GridWorld Baselines

[English](README.md) | [简体中文](README.zh-CN.md)

This experiment verifies the classical reinforcement-learning foundations used later in the agent
harness:

- A deterministic GridWorld environment
- Value iteration with a known transition model
- Model-free tabular Q-learning
- Epsilon-greedy exploration at three fixed epsilon values

## Run

From the repository root:

```bash
python experiments/week01-gridworld/run.py
```

The command rewrites `results.json` using deterministic seeds.

## Environment

```text
S . . .
. # . .
. . # .
. . . G
```

- Every ordinary step: `-1`
- Entering the goal: `+10`
- Episode limit: 50 steps
- Optimal route: 6 steps with total reward `5`

## Questions

1. Does value iteration recover an optimal six-step policy?
2. Can Q-learning recover the same path without access to the transition model?
3. How does fixed epsilon affect early and late training return?

## Result Interpretation

`results.json` records the learned greedy-policy evaluation and the mean return over the first and
last 100 training episodes. The greedy evaluation is separated from exploratory training returns so
that exploration cost is not mistaken for policy quality.
