"""Tabular Q-learning for the GridWorld environment."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from verifiable_agent_lab.environments import Action, GridWorld, State


@dataclass(frozen=True)
class QLearningConfig:
    """Hyperparameters for tabular Q-learning."""

    episodes: int = 1_500
    alpha: float = 0.2
    gamma: float = 0.95
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995
    max_steps_per_episode: int = 50

    def __post_init__(self) -> None:
        if self.episodes <= 0:
            raise ValueError("episodes must be positive")
        if not 0.0 < self.alpha <= 1.0:
            raise ValueError("alpha must satisfy 0 < alpha <= 1")
        if not 0.0 <= self.gamma < 1.0:
            raise ValueError("gamma must satisfy 0 <= gamma < 1")
        if not 0.0 <= self.epsilon_end <= self.epsilon_start <= 1.0:
            raise ValueError("epsilon values must satisfy 0 <= end <= start <= 1")
        if not 0.0 < self.epsilon_decay <= 1.0:
            raise ValueError("epsilon_decay must satisfy 0 < decay <= 1")
        if self.max_steps_per_episode <= 0:
            raise ValueError("max_steps_per_episode must be positive")


@dataclass(frozen=True)
class QLearningResult:
    """Outputs produced by a Q-learning training run."""

    q_values: NDArray[np.float64]
    policy: NDArray[np.int64]
    episode_returns: NDArray[np.float64]
    episode_lengths: NDArray[np.int64]
    final_epsilon: float

    def action_for(self, state: State) -> Action:
        """Return the learned greedy action for a non-terminal state."""

        action_index = int(self.policy[state])
        if action_index < 0:
            raise ValueError(f"policy has no action for state {state}")
        return Action(action_index)


def train_q_learning(
    env: GridWorld,
    *,
    config: QLearningConfig | None = None,
    seed: int = 42,
) -> QLearningResult:
    """Train a tabular Q-learning agent with epsilon-greedy exploration."""

    training_config = config or QLearningConfig()
    rng = np.random.default_rng(seed)
    q_values = np.zeros((env.height, env.width, len(env.actions)), dtype=np.float64)
    episode_returns = np.zeros(training_config.episodes, dtype=np.float64)
    episode_lengths = np.zeros(training_config.episodes, dtype=np.int64)
    epsilon = training_config.epsilon_start

    for episode in range(training_config.episodes):
        state, _ = env.reset(seed=seed + episode)

        for step in range(1, training_config.max_steps_per_episode + 1):
            action = _epsilon_greedy_action(q_values, state, epsilon, rng)
            next_state, reward, terminated, truncated, _ = env.step(action)
            stopped = terminated or truncated or step >= training_config.max_steps_per_episode

            best_next_value = 0.0 if stopped else float(np.max(q_values[next_state]))
            target = reward + training_config.gamma * best_next_value
            current = q_values[state][int(action)]
            q_values[state][int(action)] = current + training_config.alpha * (target - current)

            episode_returns[episode] += reward
            episode_lengths[episode] = step
            state = next_state
            if stopped:
                break

        epsilon = max(training_config.epsilon_end, epsilon * training_config.epsilon_decay)

    policy = _greedy_policy(env, q_values)
    return QLearningResult(
        q_values=q_values,
        policy=policy,
        episode_returns=episode_returns,
        episode_lengths=episode_lengths,
        final_epsilon=epsilon,
    )


def _epsilon_greedy_action(
    q_values: NDArray[np.float64],
    state: State,
    epsilon: float,
    rng: np.random.Generator,
) -> Action:
    if rng.random() < epsilon:
        return Action(int(rng.integers(len(Action))))

    state_values = q_values[state]
    best_indices = np.flatnonzero(np.isclose(state_values, np.max(state_values)))
    return Action(int(rng.choice(best_indices)))


def _greedy_policy(env: GridWorld, q_values: NDArray[np.float64]) -> NDArray[np.int64]:
    policy = np.full((env.height, env.width), -1, dtype=np.int64)
    for state in env.states:
        if state != env.goal:
            policy[state] = int(np.argmax(q_values[state]))
    return policy
