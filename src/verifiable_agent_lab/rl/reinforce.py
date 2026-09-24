"""A framework-free NumPy implementation of REINFORCE.

The environment is deliberately represented by a small protocol compatible with
Gymnasium.  Gymnasium supplies CartPole in the experiment, while every policy,
return, baseline, gradient, and optimizer update in this module is implemented
directly with NumPy.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class DiscreteEnvironment(Protocol):
    """The subset of the Gymnasium API needed by this implementation."""

    action_space: Any
    observation_space: Any

    def reset(self, *, seed: int | None = None) -> tuple[Any, dict[str, Any]]: ...

    def step(self, action: int) -> tuple[Any, float, bool, bool, dict[str, Any]]: ...


@dataclass(frozen=True)
class ReinforceConfig:
    """Hyperparameters shared by vanilla and baseline REINFORCE."""

    episodes: int = 500
    gamma: float = 0.99
    policy_learning_rate: float = 0.02
    value_learning_rate: float = 0.03
    batch_episodes: int = 10
    max_steps_per_episode: int = 500
    use_baseline: bool = False
    normalize_advantages: bool = True
    value_updates_per_batch: int = 5

    def __post_init__(self) -> None:
        if self.episodes <= 0:
            raise ValueError("episodes must be positive")
        if not 0.0 <= self.gamma <= 1.0:
            raise ValueError("gamma must satisfy 0 <= gamma <= 1")
        if self.policy_learning_rate <= 0.0:
            raise ValueError("policy_learning_rate must be positive")
        if self.value_learning_rate <= 0.0:
            raise ValueError("value_learning_rate must be positive")
        if self.batch_episodes <= 0:
            raise ValueError("batch_episodes must be positive")
        if self.max_steps_per_episode <= 0:
            raise ValueError("max_steps_per_episode must be positive")
        if self.value_updates_per_batch <= 0:
            raise ValueError("value_updates_per_batch must be positive")


@dataclass(frozen=True)
class ReinforceResult:
    """Learned parameters and metrics from a complete training run."""

    policy: SoftmaxPolicy
    value_baseline: LinearValueBaseline | None
    episode_returns: FloatArray
    episode_lengths: IntArray
    batch_policy_losses: FloatArray
    batch_value_losses: FloatArray
    batch_advantage_variances: FloatArray
    batch_gradient_norms: FloatArray


class _Adam:
    """Minimal Adam optimizer supporting either ascent or descent."""

    def __init__(
        self,
        shape: tuple[int, ...],
        learning_rate: float,
        *,
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
    ) -> None:
        self.learning_rate = learning_rate
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.first_moment = np.zeros(shape, dtype=np.float64)
        self.second_moment = np.zeros(shape, dtype=np.float64)
        self.steps = 0

    def update(self, parameter: FloatArray, gradient: FloatArray, *, ascent: bool) -> None:
        self.steps += 1
        self.first_moment *= self.beta1
        self.first_moment += (1.0 - self.beta1) * gradient
        self.second_moment *= self.beta2
        self.second_moment += (1.0 - self.beta2) * np.square(gradient)

        corrected_first = self.first_moment / (1.0 - self.beta1**self.steps)
        corrected_second = self.second_moment / (1.0 - self.beta2**self.steps)
        direction = self.learning_rate * corrected_first / (
            np.sqrt(corrected_second) + self.epsilon
        )
        if ascent:
            parameter += direction
        else:
            parameter -= direction


class SoftmaxPolicy:
    """A linear categorical policy trained with the score-function gradient."""

    def __init__(
        self,
        observation_size: int,
        action_count: int,
        *,
        learning_rate: float,
        rng: np.random.Generator,
    ) -> None:
        if observation_size <= 0:
            raise ValueError("observation_size must be positive")
        if action_count <= 1:
            raise ValueError("action_count must be at least two")
        self.observation_size = observation_size
        self.action_count = action_count
        self.weights = rng.normal(
            loc=0.0,
            scale=0.01,
            size=(observation_size + 1, action_count),
        )
        self._optimizer = _Adam(self.weights.shape, learning_rate)

    def probabilities(self, observations: FloatArray) -> FloatArray:
        """Return one categorical probability vector per observation."""

        features = _feature_matrix(observations, self.observation_size)
        logits = features @ self.weights
        logits -= np.max(logits, axis=1, keepdims=True)
        exponentials = np.exp(logits)
        return exponentials / np.sum(exponentials, axis=1, keepdims=True)

    def sample_action(self, observation: FloatArray, rng: np.random.Generator) -> int:
        """Sample one action from the current policy."""

        probabilities = self.probabilities(observation.reshape(1, -1))[0]
        return int(rng.choice(self.action_count, p=probabilities))

    def greedy_action(self, observation: FloatArray) -> int:
        """Return the highest-probability action for evaluation."""

        return int(np.argmax(self.probabilities(observation.reshape(1, -1))[0]))

    def update(
        self,
        observations: FloatArray,
        actions: IntArray,
        advantages: FloatArray,
    ) -> tuple[float, float]:
        """Apply one gradient-ascent step and return loss and gradient norm."""

        features = _feature_matrix(observations, self.observation_size)
        if actions.shape != (features.shape[0],):
            raise ValueError("actions must contain one item per observation")
        if advantages.shape != (features.shape[0],):
            raise ValueError("advantages must contain one item per observation")
        if np.any(actions < 0) or np.any(actions >= self.action_count):
            raise ValueError("actions contain an out-of-range index")

        probabilities = self.probabilities(observations)
        chosen = probabilities[np.arange(len(actions)), actions]
        loss = -float(np.mean(np.log(np.clip(chosen, 1e-12, 1.0)) * advantages))

        score = -probabilities
        score[np.arange(len(actions)), actions] += 1.0
        gradient = features.T @ (score * advantages[:, np.newaxis]) / len(actions)
        gradient_norm = float(np.linalg.norm(gradient))
        self._optimizer.update(self.weights, gradient, ascent=True)
        return loss, gradient_norm


class LinearValueBaseline:
    """A state-only linear value function fitted with mean-squared error."""

    def __init__(self, observation_size: int, *, learning_rate: float) -> None:
        if observation_size <= 0:
            raise ValueError("observation_size must be positive")
        self.observation_size = observation_size
        self.weights = np.zeros(observation_size + 1, dtype=np.float64)
        self._optimizer = _Adam(self.weights.shape, learning_rate)

    def predict(self, observations: FloatArray) -> FloatArray:
        """Estimate V(s) for each observation."""

        return _feature_matrix(observations, self.observation_size) @ self.weights

    def update(self, observations: FloatArray, targets: FloatArray) -> float:
        """Apply one gradient-descent step and return the pre-update MSE."""

        features = _feature_matrix(observations, self.observation_size)
        if targets.shape != (features.shape[0],):
            raise ValueError("targets must contain one item per observation")
        errors = self.predict(observations) - targets
        loss = float(np.mean(np.square(errors)))
        gradient = 2.0 * (features.T @ errors) / len(targets)
        self._optimizer.update(self.weights, gradient, ascent=False)
        return loss


def discounted_returns(rewards: FloatArray, gamma: float) -> FloatArray:
    """Compute reward-to-go G_t for one completed trajectory."""

    if rewards.ndim != 1:
        raise ValueError("rewards must be one-dimensional")
    if not 0.0 <= gamma <= 1.0:
        raise ValueError("gamma must satisfy 0 <= gamma <= 1")
    returns = np.empty_like(rewards, dtype=np.float64)
    running_return = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        running_return = float(rewards[index]) + gamma * running_return
        returns[index] = running_return
    return returns


def train_reinforce(
    env: DiscreteEnvironment,
    *,
    config: ReinforceConfig | None = None,
    seed: int = 42,
) -> ReinforceResult:
    """Train vanilla REINFORCE or REINFORCE with a learned value baseline."""

    training_config = config or ReinforceConfig()
    observation_size, action_count = _environment_dimensions(env)
    rng = np.random.default_rng(seed)
    policy = SoftmaxPolicy(
        observation_size,
        action_count,
        learning_rate=training_config.policy_learning_rate,
        rng=rng,
    )
    baseline = (
        LinearValueBaseline(
            observation_size,
            learning_rate=training_config.value_learning_rate,
        )
        if training_config.use_baseline
        else None
    )

    episode_returns = np.zeros(training_config.episodes, dtype=np.float64)
    episode_lengths = np.zeros(training_config.episodes, dtype=np.int64)
    policy_losses: list[float] = []
    value_losses: list[float] = []
    advantage_variances: list[float] = []
    gradient_norms: list[float] = []

    batch_observations: list[FloatArray] = []
    batch_actions: list[IntArray] = []
    batch_returns: list[FloatArray] = []

    for episode in range(training_config.episodes):
        observations, actions, rewards = _collect_episode(
            env,
            policy,
            rng,
            seed=seed + episode,
            max_steps=training_config.max_steps_per_episode,
        )
        episode_returns[episode] = float(np.sum(rewards))
        episode_lengths[episode] = len(rewards)
        batch_observations.append(observations)
        batch_actions.append(actions)
        batch_returns.append(discounted_returns(rewards, training_config.gamma))

        batch_is_ready = len(batch_observations) >= training_config.batch_episodes
        final_episode = episode == training_config.episodes - 1
        if not batch_is_ready and not final_episode:
            continue

        observations_array = np.concatenate(batch_observations)
        actions_array = np.concatenate(batch_actions)
        returns_array = np.concatenate(batch_returns)
        raw_advantages = returns_array.copy()
        if baseline is not None:
            raw_advantages -= baseline.predict(observations_array)

        advantage_variances.append(float(np.var(raw_advantages)))
        update_advantages = (
            _standardize(raw_advantages)
            if training_config.normalize_advantages
            else raw_advantages
        )
        policy_loss, gradient_norm = policy.update(
            observations_array,
            actions_array,
            update_advantages,
        )
        policy_losses.append(policy_loss)
        gradient_norms.append(gradient_norm)

        if baseline is None:
            value_losses.append(float("nan"))
        else:
            loss = 0.0
            for _ in range(training_config.value_updates_per_batch):
                loss = baseline.update(observations_array, returns_array)
            value_losses.append(loss)

        batch_observations.clear()
        batch_actions.clear()
        batch_returns.clear()

    return ReinforceResult(
        policy=policy,
        value_baseline=baseline,
        episode_returns=episode_returns,
        episode_lengths=episode_lengths,
        batch_policy_losses=np.asarray(policy_losses, dtype=np.float64),
        batch_value_losses=np.asarray(value_losses, dtype=np.float64),
        batch_advantage_variances=np.asarray(advantage_variances, dtype=np.float64),
        batch_gradient_norms=np.asarray(gradient_norms, dtype=np.float64),
    )


def _collect_episode(
    env: DiscreteEnvironment,
    policy: SoftmaxPolicy,
    rng: np.random.Generator,
    *,
    seed: int,
    max_steps: int,
) -> tuple[FloatArray, IntArray, FloatArray]:
    observation, _ = env.reset(seed=seed)
    current = _as_observation(observation, policy.observation_size)
    observations: list[FloatArray] = []
    actions: list[int] = []
    rewards: list[float] = []

    for _ in range(max_steps):
        action = policy.sample_action(current, rng)
        next_observation, reward, terminated, truncated, _ = env.step(action)
        observations.append(current)
        actions.append(action)
        rewards.append(float(reward))
        current = _as_observation(next_observation, policy.observation_size)
        if terminated or truncated:
            break

    return (
        np.stack(observations),
        np.asarray(actions, dtype=np.int64),
        np.asarray(rewards, dtype=np.float64),
    )


def _environment_dimensions(env: DiscreteEnvironment) -> tuple[int, int]:
    shape = getattr(env.observation_space, "shape", None)
    action_count = getattr(env.action_space, "n", None)
    if not isinstance(shape, tuple) or len(shape) != 1 or not isinstance(shape[0], int):
        raise ValueError("environment must have a one-dimensional observation space")
    if not isinstance(action_count, Integral):
        raise ValueError("environment must have a discrete action space")
    return shape[0], int(action_count)


def _as_observation(observation: Any, expected_size: int) -> FloatArray:
    array = np.asarray(observation, dtype=np.float64)
    if array.shape != (expected_size,):
        raise ValueError(f"expected observation shape {(expected_size,)}, got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError("observations must contain only finite values")
    return array


def _feature_matrix(observations: FloatArray, observation_size: int) -> FloatArray:
    array = np.asarray(observations, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != observation_size:
        raise ValueError(f"observations must have shape (n, {observation_size})")
    if len(array) == 0:
        raise ValueError("observations must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError("observations must contain only finite values")
    bias = np.ones((len(array), 1), dtype=np.float64)
    return np.concatenate((array, bias), axis=1)


def _standardize(values: FloatArray) -> FloatArray:
    standard_deviation = float(np.std(values))
    if standard_deviation < 1e-8:
        return values - np.mean(values)
    return (values - np.mean(values)) / (standard_deviation + 1e-8)
