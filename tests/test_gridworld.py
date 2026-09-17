import pytest

from verifiable_agent_lab.environments import Action, GridWorld


def test_reset_returns_start_state() -> None:
    env = GridWorld()

    state, info = env.reset()

    assert state == (0, 0)
    assert info == {}
    assert env.step_count == 0


def test_boundaries_and_obstacles_block_movement() -> None:
    env = GridWorld()
    env.reset()

    state, reward, terminated, truncated, _ = env.step(Action.UP)
    assert state == (0, 0)
    assert reward == -1.0
    assert not terminated
    assert not truncated

    env.step(Action.DOWN)
    state, *_ = env.step(Action.RIGHT)
    assert state == (1, 0)


def test_known_shortest_path_reaches_goal() -> None:
    env = GridWorld()
    env.reset()
    actions = [
        Action.RIGHT,
        Action.RIGHT,
        Action.RIGHT,
        Action.DOWN,
        Action.DOWN,
        Action.DOWN,
    ]

    total_reward = 0.0
    for action in actions:
        state, reward, terminated, truncated, _ = env.step(action)
        total_reward += reward

    assert state == env.goal
    assert terminated
    assert not truncated
    assert total_reward == 5.0

    with pytest.raises(RuntimeError, match="call reset"):
        env.step(Action.LEFT)


def test_episode_truncates_at_step_limit() -> None:
    env = GridWorld(max_steps=2)
    env.reset()

    env.step(Action.UP)
    _, _, terminated, truncated, _ = env.step(Action.UP)

    assert not terminated
    assert truncated

    with pytest.raises(RuntimeError, match="call reset"):
        env.step(Action.RIGHT)


def test_render_contains_agent_goal_and_obstacles() -> None:
    rendered = GridWorld().render()

    assert "A" in rendered
    assert "G" in rendered
    assert rendered.count("#") == 2
