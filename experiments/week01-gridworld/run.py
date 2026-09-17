"""Run deterministic Week 1 GridWorld baselines and write results.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import numpy as np

from verifiable_agent_lab.environments import GridWorld
from verifiable_agent_lab.rl import QLearningConfig, train_q_learning, value_iteration


class Evaluation(TypedDict):
    reached_goal: bool
    steps: int
    total_reward: float
    path: list[list[int]]


def evaluate_policy(env: GridWorld, policy: np.ndarray) -> Evaluation:
    """Evaluate a deterministic policy without exploration."""

    state, _ = env.reset()
    path = [list(state)]
    total_reward = 0.0
    reached_goal = False

    for step in range(1, env.max_steps + 1):
        action_index = int(policy[state])
        if action_index < 0:
            return {
                "reached_goal": False,
                "steps": step - 1,
                "total_reward": total_reward,
                "path": path,
            }

        state, reward, terminated, truncated, _ = env.step(action_index)
        path.append(list(state))
        total_reward += reward
        if terminated or truncated:
            reached_goal = terminated
            return {
                "reached_goal": reached_goal,
                "steps": step,
                "total_reward": total_reward,
                "path": path,
            }

    raise AssertionError("evaluation exceeded the environment step limit")


def main() -> None:
    env = GridWorld()
    value_result = value_iteration(env)
    q_learning_runs: list[dict[str, object]] = []

    for epsilon in (0.01, 0.1, 0.3):
        config = QLearningConfig(
            episodes=1_500,
            epsilon_start=epsilon,
            epsilon_end=epsilon,
            epsilon_decay=1.0,
        )
        training_result = train_q_learning(env, config=config, seed=42)
        q_learning_runs.append(
            {
                "epsilon": epsilon,
                "episodes": config.episodes,
                "mean_return_first_100": round(
                    float(np.mean(training_result.episode_returns[:100])), 4
                ),
                "mean_return_last_100": round(
                    float(np.mean(training_result.episode_returns[-100:])), 4
                ),
                "greedy_evaluation": evaluate_policy(env, training_result.policy),
            }
        )

    results = {
        "seed": 42,
        "environment": {
            "shape": [env.height, env.width],
            "start": list(env.start),
            "goal": list(env.goal),
            "obstacles": [list(state) for state in sorted(env.obstacles)],
            "step_reward": env.step_reward,
            "goal_reward": env.goal_reward,
            "max_steps": env.max_steps,
        },
        "value_iteration": {
            "gamma": 0.95,
            "converged": value_result.converged,
            "iterations": value_result.iterations,
            "evaluation": evaluate_policy(env, value_result.policy),
        },
        "q_learning": q_learning_runs,
    }

    output_path = Path(__file__).with_name("results.json")
    output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
