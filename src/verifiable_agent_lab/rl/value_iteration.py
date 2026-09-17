"""Value iteration for deterministic GridWorld environments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from verifiable_agent_lab.environments import Action, GridWorld, State


@dataclass(frozen=True)
class ValueIterationResult:
    """Outputs produced by value iteration."""

    values: NDArray[np.float64]
    policy: NDArray[np.int64]
    iterations: int
    converged: bool

    def action_for(self, state: State) -> Action:
        """Return the greedy action for a non-terminal traversable state."""

        action_index = int(self.policy[state])
        if action_index < 0:
            raise ValueError(f"policy has no action for state {state}")
        return Action(action_index)


def value_iteration(
    env: GridWorld,
    *,
    gamma: float = 0.95,
    tolerance: float = 1e-10,
    max_iterations: int = 10_000,
) -> ValueIterationResult:
    """Compute an optimal value function and deterministic greedy policy."""

    if not 0.0 <= gamma < 1.0:
        raise ValueError("gamma must satisfy 0 <= gamma < 1")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")

    values = np.full((env.height, env.width), np.nan, dtype=np.float64)
    values[env.state_mask()] = 0.0
    policy = np.full((env.height, env.width), -1, dtype=np.int64)

    converged = False
    completed_iterations = 0

    for iteration in range(1, max_iterations + 1):
        delta = 0.0
        updated_values = values.copy()

        for state in env.states:
            if state == env.goal:
                continue

            action_values = np.asarray(
                [_action_value(env, values, state, action, gamma) for action in env.actions],
                dtype=np.float64,
            )
            best_action_index = int(np.argmax(action_values))
            best_value = float(action_values[best_action_index])
            updated_values[state] = best_value
            policy[state] = int(env.actions[best_action_index])
            delta = max(delta, abs(best_value - float(values[state])))

        values = updated_values
        completed_iterations = iteration
        if delta < tolerance:
            converged = True
            break

    return ValueIterationResult(
        values=values,
        policy=policy,
        iterations=completed_iterations,
        converged=converged,
    )


def _action_value(
    env: GridWorld,
    values: NDArray[np.float64],
    state: State,
    action: Action,
    gamma: float,
) -> float:
    next_state, reward, terminated = env.transition(state, action)
    return reward if terminated else reward + gamma * float(values[next_state])
