"""A deterministic GridWorld with a Gym-style interface."""

from __future__ import annotations

from enum import IntEnum
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

State: TypeAlias = tuple[int, int]


class Action(IntEnum):
    """Actions supported by :class:`GridWorld`."""

    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3


_ACTION_DELTAS: dict[Action, State] = {
    Action.UP: (-1, 0),
    Action.RIGHT: (0, 1),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
}


class GridWorld:
    """A small deterministic grid used for dynamic-programming and RL exercises.

    The default map is::

        S . . .
        . # . .
        . . # .
        . . . G

    Every non-terminal step receives ``step_reward``. Entering the goal receives
    ``goal_reward`` and terminates the episode. Attempts to cross a boundary or
    enter an obstacle leave the agent in its current state.
    """

    actions: tuple[Action, ...] = tuple(Action)

    def __init__(
        self,
        *,
        height: int = 4,
        width: int = 4,
        start: State = (0, 0),
        goal: State = (3, 3),
        obstacles: frozenset[State] | None = None,
        step_reward: float = -1.0,
        goal_reward: float = 10.0,
        max_steps: int = 50,
    ) -> None:
        if height <= 0 or width <= 0:
            raise ValueError("height and width must be positive")
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")

        self.height = height
        self.width = width
        self.start = start
        self.goal = goal
        self.obstacles = obstacles if obstacles is not None else frozenset({(1, 1), (2, 2)})
        self.step_reward = float(step_reward)
        self.goal_reward = float(goal_reward)
        self.max_steps = max_steps

        if not self._in_bounds(start) or not self._in_bounds(goal):
            raise ValueError("start and goal must be inside the grid")
        if start == goal:
            raise ValueError("start and goal must be different")
        if start in self.obstacles or goal in self.obstacles:
            raise ValueError("start and goal cannot be obstacles")
        if any(not self._in_bounds(state) for state in self.obstacles):
            raise ValueError("all obstacles must be inside the grid")

        self._states = tuple(
            (row, column)
            for row in range(height)
            for column in range(width)
            if (row, column) not in self.obstacles
        )
        self._state = start
        self._step_count = 0
        self._episode_over = False

    @property
    def state(self) -> State:
        """Return the current environment state."""

        return self._state

    @property
    def step_count(self) -> int:
        """Return the number of actions taken in the current episode."""

        return self._step_count

    @property
    def states(self) -> tuple[State, ...]:
        """Return all traversable states, including the terminal goal state."""

        return self._states

    def reset(self, *, seed: int | None = None) -> tuple[State, dict[str, object]]:
        """Reset the episode and return ``(state, info)``.

        ``seed`` is accepted for API compatibility. The environment itself is
        deterministic, so the value does not affect transitions.
        """

        del seed
        self._state = self.start
        self._step_count = 0
        self._episode_over = False
        return self._state, {}

    def transition(self, state: State, action: Action | int) -> tuple[State, float, bool]:
        """Return the deterministic transition without mutating the environment."""

        if state not in self._states:
            raise ValueError(f"invalid state: {state}")

        normalized_action = self._normalize_action(action)
        if state == self.goal:
            return state, 0.0, True

        row_delta, column_delta = _ACTION_DELTAS[normalized_action]
        candidate = (state[0] + row_delta, state[1] + column_delta)
        next_state = state if not self._is_traversable(candidate) else candidate
        terminated = next_state == self.goal
        reward = self.goal_reward if terminated else self.step_reward
        return next_state, reward, terminated

    def step(
        self, action: Action | int
    ) -> tuple[State, float, bool, bool, dict[str, object]]:
        """Apply an action and return a Gym-style transition tuple.

        Returns ``(state, reward, terminated, truncated, info)``.
        """

        if self._episode_over:
            raise RuntimeError("episode has ended; call reset() before step()")

        next_state, reward, terminated = self.transition(self._state, action)
        self._state = next_state
        self._step_count += 1
        truncated = not terminated and self._step_count >= self.max_steps
        self._episode_over = terminated or truncated
        return next_state, reward, terminated, truncated, {"step_count": self._step_count}

    def state_mask(self) -> NDArray[np.bool_]:
        """Return a boolean array whose true cells are traversable states."""

        mask = np.ones((self.height, self.width), dtype=np.bool_)
        for obstacle in self.obstacles:
            mask[obstacle] = False
        return mask

    def render(self, *, state: State | None = None) -> str:
        """Return an ASCII representation of the grid."""

        agent_state = self._state if state is None else state
        rows: list[str] = []
        for row in range(self.height):
            cells: list[str] = []
            for column in range(self.width):
                cell = (row, column)
                if cell == agent_state:
                    cells.append("A")
                elif cell == self.start:
                    cells.append("S")
                elif cell == self.goal:
                    cells.append("G")
                elif cell in self.obstacles:
                    cells.append("#")
                else:
                    cells.append(".")
            rows.append(" ".join(cells))
        return "\n".join(rows)

    def _in_bounds(self, state: State) -> bool:
        return 0 <= state[0] < self.height and 0 <= state[1] < self.width

    def _is_traversable(self, state: State) -> bool:
        return self._in_bounds(state) and state not in self.obstacles

    @staticmethod
    def _normalize_action(action: Action | int) -> Action:
        try:
            return Action(action)
        except ValueError as error:
            raise ValueError(f"invalid action: {action}") from error
