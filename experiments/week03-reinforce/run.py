"""Compare vanilla REINFORCE with a learned value baseline on CartPole-v1."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from verifiable_agent_lab.rl import ReinforceConfig, ReinforceResult, train_reinforce

EXPERIMENT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--seeds", default="7,42,329")
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--policy-learning-rate", type=float, default=0.02)
    parser.add_argument("--value-learning-rate", type=float, default=0.03)
    parser.add_argument("--batch-episodes", type=int, default=10)
    parser.add_argument("--value-updates-per-batch", type=int, default=5)
    parser.add_argument("--evaluation-episodes", type=int, default=20)
    parser.add_argument("--smoothing-window", type=int, default=25)
    parser.add_argument("--output", type=Path, default=EXPERIMENT_DIR / "results.json")
    parser.add_argument("--plot", type=Path, default=EXPERIMENT_DIR / "learning-curves.svg")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seeds = _parse_seeds(args.seeds)
    gym = _load_gymnasium()
    variants: dict[str, dict[str, Any]] = {}

    for name, use_baseline in (("vanilla", False), ("value_baseline", True)):
        runs: list[dict[str, Any]] = []
        curves: list[np.ndarray] = []
        for seed in seeds:
            env = gym.make("CartPole-v1")
            config = ReinforceConfig(
                episodes=args.episodes,
                gamma=args.gamma,
                policy_learning_rate=args.policy_learning_rate,
                value_learning_rate=args.value_learning_rate,
                batch_episodes=args.batch_episodes,
                use_baseline=use_baseline,
                value_updates_per_batch=args.value_updates_per_batch,
            )
            try:
                result = train_reinforce(env, config=config, seed=seed)
            finally:
                env.close()

            evaluation_returns = _evaluate_policy(
                gym,
                result,
                seed=seed + 100_000,
                episodes=args.evaluation_episodes,
            )
            curves.append(result.episode_returns)
            runs.append(_summarize_run(seed, result, evaluation_returns))
            print(
                f"{name:14s} seed={seed:3d} "
                f"last100={np.mean(result.episode_returns[-100:]):7.2f} "
                f"eval={np.mean(evaluation_returns):7.2f}"
            )

        curve_array = np.stack(curves)
        variants[name] = {
            "runs": runs,
            "aggregate": {
                "mean_last_100_return": _rounded(
                    np.mean(curve_array[:, -min(100, args.episodes) :])
                ),
                "std_last_100_return_across_seeds": _rounded(
                    np.std(np.mean(curve_array[:, -min(100, args.episodes) :], axis=1))
                ),
                "mean_evaluation_return": _rounded(
                    np.mean([run["evaluation_mean_return"] for run in runs])
                ),
                "mean_raw_advantage_variance": _rounded(
                    np.mean([run["mean_raw_advantage_variance"] for run in runs])
                ),
                "mean_policy_gradient_norm": _rounded(
                    np.mean([run["mean_policy_gradient_norm"] for run in runs])
                ),
            },
            "mean_return_by_episode": np.mean(curve_array, axis=0).round(4).tolist(),
            "std_return_by_episode": np.std(curve_array, axis=0).round(4).tolist(),
        }

    vanilla = variants["vanilla"]["aggregate"]
    with_baseline = variants["value_baseline"]["aggregate"]
    results = {
        "experiment": "REINFORCE versus REINFORCE with a value baseline",
        "environment": "CartPole-v1",
        "implementation": "NumPy policy gradient and value function; Gymnasium environment only",
        "seeds": seeds,
        "config": {
            "episodes": args.episodes,
            "gamma": args.gamma,
            "policy_learning_rate": args.policy_learning_rate,
            "value_learning_rate": args.value_learning_rate,
            "batch_episodes": args.batch_episodes,
            "value_updates_per_batch": args.value_updates_per_batch,
            "normalize_advantages": True,
            "evaluation_episodes": args.evaluation_episodes,
        },
        "variants": variants,
        "comparison": {
            "baseline_minus_vanilla_last_100_return": _rounded(
                with_baseline["mean_last_100_return"] - vanilla["mean_last_100_return"]
            ),
            "baseline_minus_vanilla_evaluation_return": _rounded(
                with_baseline["mean_evaluation_return"] - vanilla["mean_evaluation_return"]
            ),
            "raw_advantage_variance_ratio_baseline_over_vanilla": _rounded(
                with_baseline["mean_raw_advantage_variance"]
                / vanilla["mean_raw_advantage_variance"]
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_learning_curve_svg(
        args.plot,
        variants,
        smoothing_window=args.smoothing_window,
    )
    print(f"Wrote {args.output}")
    print(f"Wrote {args.plot}")


def _summarize_run(
    seed: int,
    result: ReinforceResult,
    evaluation_returns: np.ndarray,
) -> dict[str, Any]:
    final_window = min(100, len(result.episode_returns))
    value_losses = result.batch_value_losses[np.isfinite(result.batch_value_losses)]
    return {
        "seed": seed,
        "mean_first_100_return": _rounded(np.mean(result.episode_returns[:final_window])),
        "mean_last_100_return": _rounded(np.mean(result.episode_returns[-final_window:])),
        "evaluation_mean_return": _rounded(np.mean(evaluation_returns)),
        "evaluation_std_return": _rounded(np.std(evaluation_returns)),
        "mean_raw_advantage_variance": _rounded(
            np.mean(result.batch_advantage_variances)
        ),
        "mean_policy_gradient_norm": _rounded(np.mean(result.batch_gradient_norms)),
        "final_value_loss": _rounded(value_losses[-1]) if len(value_losses) else None,
        "policy_weights": result.policy.weights.round(6).tolist(),
        "value_weights": (
            result.value_baseline.weights.round(6).tolist()
            if result.value_baseline is not None
            else None
        ),
    }


def _evaluate_policy(
    gym: Any,
    result: ReinforceResult,
    *,
    seed: int,
    episodes: int,
) -> np.ndarray:
    env = gym.make("CartPole-v1")
    returns = np.zeros(episodes, dtype=np.float64)
    try:
        for episode in range(episodes):
            observation, _ = env.reset(seed=seed + episode)
            for _ in range(500):
                action = result.policy.greedy_action(
                    np.asarray(observation, dtype=np.float64)
                )
                observation, reward, terminated, truncated, _ = env.step(action)
                returns[episode] += float(reward)
                if terminated or truncated:
                    break
    finally:
        env.close()
    return returns


def _parse_seeds(raw: str) -> list[int]:
    try:
        seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    except ValueError as error:
        raise ValueError("--seeds must be a comma-separated list of integers") from error
    if not seeds:
        raise ValueError("--seeds must contain at least one integer")
    if len(set(seeds)) != len(seeds):
        raise ValueError("--seeds must be unique")
    return seeds


def _load_gymnasium() -> Any:
    try:
        return importlib.import_module("gymnasium")
    except ModuleNotFoundError as error:
        raise SystemExit(
            'Gymnasium is required for this experiment. Run: pip install -e ".[dev,rl]"'
        ) from error


def _rounded(value: float | np.floating[Any]) -> float:
    return round(float(value), 6)


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 0:
        raise ValueError("smoothing window must be positive")
    if window == 1:
        return values.copy()
    cumulative = np.cumsum(np.insert(values, 0, 0.0))
    averaged = (cumulative[window:] - cumulative[:-window]) / window
    prefix = np.array([np.mean(values[: index + 1]) for index in range(window - 1)])
    return np.concatenate((prefix, averaged))


def _write_learning_curve_svg(
    path: Path,
    variants: dict[str, dict[str, Any]],
    *,
    smoothing_window: int,
) -> None:
    width, height = 900, 520
    left, right, top, bottom = 75, 25, 45, 65
    plot_width = width - left - right
    plot_height = height - top - bottom
    colors = {"vanilla": "#d97706", "value_baseline": "#2563eb"}
    series = {
        name: _moving_average(np.asarray(data["mean_return_by_episode"]), smoothing_window)
        for name, data in variants.items()
    }
    episode_count = len(next(iter(series.values())))
    maximum = max(500.0, max(float(np.max(values)) for values in series.values()))

    def point(index: int, value: float) -> tuple[float, float]:
        x = left + index * plot_width / max(1, episode_count - 1)
        y = top + (maximum - value) * plot_height / maximum
        return x, y

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="450" y="27" text-anchor="middle" font-family="sans-serif" '
        'font-size="20">CartPole-v1: REINFORCE comparison</text>',
    ]
    for tick in range(0, 501, 100):
        y = top + (maximum - tick) * plot_height / maximum
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" '
            'stroke="#e5e7eb"/>'
        )
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="12">{tick}</text>'
        )
    for name, values in series.items():
        points = " ".join(
            f"{x:.2f},{y:.2f}" for x, y in (point(i, float(v)) for i, v in enumerate(values))
        )
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{colors[name]}" '
            'stroke-width="3"/>'
        )
    lines.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" '
            'stroke="#111827"/>',
            f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" '
            f'y2="{height - bottom}" stroke="#111827"/>',
            f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle" '
            'font-family="sans-serif" font-size="14">Episode</text>',
            f'<text x="18" y="{height / 2}" text-anchor="middle" '
            'font-family="sans-serif" font-size="14" '
            'transform="rotate(-90 18 260)">Mean return</text>',
            '<line x1="590" y1="58" x2="625" y2="58" stroke="#d97706" stroke-width="3"/>',
            '<text x="633" y="63" font-family="sans-serif" font-size="13">Vanilla</text>',
            '<line x1="705" y1="58" x2="740" y2="58" stroke="#2563eb" stroke-width="3"/>',
            '<text x="748" y="63" font-family="sans-serif" font-size="13">Value baseline</text>',
            f'<text x="{width - right}" y="{height - bottom + 24}" text-anchor="end" '
            f'font-family="sans-serif" font-size="12">{episode_count}</text>',
            f'<text x="{left}" y="{height - bottom + 24}" text-anchor="middle" '
            'font-family="sans-serif" font-size="12">1</text>',
            '</svg>',
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
