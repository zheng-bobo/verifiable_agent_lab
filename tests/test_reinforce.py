from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from verifiable_agent_lab.rl import (
    LinearValueBaseline,
    ReinforceConfig,
    SoftmaxPolicy,
    discounted_returns,
    train_reinforce,
)


@dataclass(frozen=True)
class _BoxSpace:
    shape: tuple[int, ...]


@dataclass(frozen=True)
class _DiscreteSpace:
    n: int


class _OneStepBandit:
    """Action 1 always pays one; action 0 always pays zero."""

    observation_space = _BoxSpace((1,))
    action_space = _DiscreteSpace(2)

    def reset(self, *, seed: int | None = None) -> tuple[np.ndarray, dict[str, object]]:
        del seed
        return np.array([1.0]), {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, object]]:
        return np.array([1.0]), float(action == 1), True, False, {}


def test_discounted_returns_uses_reward_to_go() -> None:
    rewards = np.array([1.0, 2.0, 3.0])

    returns = discounted_returns(rewards, gamma=0.5)

    np.testing.assert_allclose(returns, [2.75, 3.5, 3.0])


def test_policy_update_increases_probability_of_positive_action() -> None:
    rng = np.random.default_rng(7)
    policy = SoftmaxPolicy(1, 2, learning_rate=0.01, rng=rng)
    observations = np.array([[1.0], [1.0]])
    before = policy.probabilities(observations[:1])[0, 1]

    policy.update(
        observations,
        np.array([1, 1], dtype=np.int64),
        np.array([1.0, 1.0]),
    )

    after = policy.probabilities(observations[:1])[0, 1]
    assert after > before


def test_value_baseline_moves_predictions_toward_returns() -> None:
    baseline = LinearValueBaseline(1, learning_rate=0.05)
    observations = np.array([[0.0], [1.0], [2.0]])
    targets = np.array([1.0, 2.0, 3.0])
    before = float(np.mean(np.square(baseline.predict(observations) - targets)))

    for _ in range(20):
        baseline.update(observations, targets)

    after = float(np.mean(np.square(baseline.predict(observations) - targets)))
    assert after < before


@pytest.mark.parametrize("use_baseline", [False, True])
def test_reinforce_is_reproducible_and_learns_bandit(use_baseline: bool) -> None:
    config = ReinforceConfig(
        episodes=120,
        gamma=1.0,
        policy_learning_rate=0.03,
        value_learning_rate=0.03,
        batch_episodes=5,
        max_steps_per_episode=1,
        use_baseline=use_baseline,
    )

    first = train_reinforce(_OneStepBandit(), config=config, seed=329)
    second = train_reinforce(_OneStepBandit(), config=config, seed=329)

    np.testing.assert_allclose(first.policy.weights, second.policy.weights)
    np.testing.assert_allclose(first.episode_returns, second.episode_returns)
    assert first.policy.greedy_action(np.array([1.0])) == 1
    assert np.mean(first.episode_returns[-40:]) > np.mean(first.episode_returns[:40])
    assert (first.value_baseline is not None) is use_baseline


def test_reinforce_config_rejects_invalid_gamma() -> None:
    with pytest.raises(ValueError, match="gamma"):
        ReinforceConfig(gamma=1.1)
