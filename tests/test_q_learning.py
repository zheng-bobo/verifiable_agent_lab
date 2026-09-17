import numpy as np
import pytest

from verifiable_agent_lab.environments import GridWorld
from verifiable_agent_lab.rl import QLearningConfig, train_q_learning


def test_q_learning_is_reproducible_with_a_fixed_seed() -> None:
    config = QLearningConfig(episodes=300)

    first = train_q_learning(GridWorld(), config=config, seed=7)
    second = train_q_learning(GridWorld(), config=config, seed=7)

    np.testing.assert_allclose(first.q_values, second.q_values)
    np.testing.assert_array_equal(first.policy, second.policy)
    np.testing.assert_allclose(first.episode_returns, second.episode_returns)


def test_q_learning_learns_a_shortest_path() -> None:
    config = QLearningConfig(episodes=1_500)
    result = train_q_learning(GridWorld(), config=config, seed=42)
    env = GridWorld()
    state, _ = env.reset()

    steps = 0
    for step in range(1, env.max_steps + 1):
        steps = step
        state, _, terminated, truncated, _ = env.step(result.action_for(state))
        if terminated or truncated:
            break

    assert state == env.goal
    assert steps == 6
    assert np.mean(result.episode_returns[-100:]) > np.mean(result.episode_returns[:100])


def test_q_learning_config_rejects_invalid_epsilon_range() -> None:
    with pytest.raises(ValueError, match="epsilon"):
        QLearningConfig(epsilon_start=0.1, epsilon_end=0.2)
