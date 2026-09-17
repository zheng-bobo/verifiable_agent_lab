import numpy as np
import pytest

from verifiable_agent_lab.environments import GridWorld
from verifiable_agent_lab.rl import value_iteration


def test_value_iteration_converges_to_shortest_path() -> None:
    env = GridWorld()

    result = value_iteration(env)

    assert result.converged
    assert result.iterations > 0
    assert result.values[env.goal] == 0.0
    assert np.isnan(result.values[1, 1])

    state, _ = env.reset()
    states = [state]
    for _ in range(env.max_steps):
        state, _, terminated, truncated, _ = env.step(result.action_for(state))
        states.append(state)
        if terminated or truncated:
            break

    assert state == env.goal
    assert len(states) - 1 == 6


def test_value_iteration_is_deterministic() -> None:
    env = GridWorld()

    first = value_iteration(env)
    second = value_iteration(env)

    np.testing.assert_allclose(first.values, second.values, equal_nan=True)
    np.testing.assert_array_equal(first.policy, second.policy)


def test_value_iteration_validates_gamma() -> None:
    with pytest.raises(ValueError, match="gamma"):
        value_iteration(GridWorld(), gamma=1.0)
