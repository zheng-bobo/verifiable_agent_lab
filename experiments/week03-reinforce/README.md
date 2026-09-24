# Week 3: REINFORCE and a Value Baseline From Scratch

[English](README.md) | [简体中文](README.zh-CN.md)

This experiment compares two algorithms on `CartPole-v1`:

1. Vanilla REINFORCE, which weights the policy gradient with Monte Carlo reward-to-go.
2. REINFORCE with a value baseline, which uses `G_t - V(s_t)` and fits `V(s)` to observed returns.

The policy, returns, baseline, gradients, and Adam updates are implemented directly in NumPy.
Gymnasium supplies only the environment; PyTorch, JAX, Stable-Baselines3, and automatic
differentiation are not used.

## Install and Run

From the repository root:

```bash
python -m pip install -e ".[dev,rl]"
python experiments/week03-reinforce/run.py
```

For a quick smoke test:

```bash
python experiments/week03-reinforce/run.py \
  --episodes 50 \
  --seeds 7 \
  --evaluation-episodes 5 \
  --output /tmp/reinforce-smoke.json \
  --plot /tmp/reinforce-smoke.svg
```

The default comparison trains three seeds for 500 episodes each and writes:

- `results.json`: configuration, per-seed metrics, aggregate results, and learned parameters.
- `learning-curves.svg`: 25-episode-smoothed training curves for both variants.

CartPole has a four-dimensional observation and two discrete actions. It awards `+1` for every
surviving step and caps `v1` at 500 steps. See the
[Gymnasium CartPole documentation](https://gymnasium.farama.org/environments/classic_control/cart_pole/).

## Suggested Code Order

1. `discounted_returns()` computes reward-to-go backwards.
2. `SoftmaxPolicy.probabilities()` converts linear logits to action probabilities.
3. `SoftmaxPolicy.update()` explicitly evaluates `grad log pi(a|s)` and performs gradient ascent.
4. `LinearValueBaseline` fits `V(s)` by mean-squared error.
5. `train_reinforce()` collects trajectories, forms batches, computes advantages, and updates both
   learners.
6. `experiments/week03-reinforce/run.py` runs paired seeds and deterministic greedy evaluation.

The core implementation is `src/verifiable_agent_lab/rl/reinforce.py`.

## Vanilla REINFORCE

Reward-to-go is:

```text
G_t = r_t + gamma r_{t+1} + gamma^2 r_{t+2} + ...
```

The Monte Carlo policy-gradient estimate is:

```text
grad J(theta) ~= sum_t G_t grad log pi_theta(a_t | s_t)
```

For the softmax policy, the code directly constructs:

```text
d log pi(a|s) / d logits = one_hot(a) - pi(.|s)
```

## Value Baseline

The baseline variant replaces the return with an advantage estimate:

```text
A_t = G_t - V_phi(s_t)
grad J(theta) ~= sum_t A_t grad log pi_theta(a_t | s_t)
```

A state-only baseline does not change the expected policy gradient because:

```text
E_a[b(s) grad log pi(a|s)]
= b(s) sum_a pi(a|s) grad log pi(a|s)
= b(s) grad sum_a pi(a|s)
= 0
```

If `V(s)` predicts return well, it can reduce Monte Carlo variance. It is trained with:

```text
L_value = mean((V_phi(s_t) - G_t)^2)
```

The experiment computes advantages with the pre-update baseline, then fits the value function to the
current batch's returns.

## Advantage Normalization

Both variants standardize the advantages used for each policy update. This keeps the gradient scale
stable as CartPole episodes grow. `mean_raw_advantage_variance` is measured before standardization,
so it still exposes how much variation the learned baseline removes. The unbiasedness derivation
above applies to the unnormalized state-only baseline; normalization with sample statistics from the
current batch is an additional practical heuristic with finite-sample effects.

## Default Results

The committed `results.json` uses seeds `7`, `42`, and `329`:

| Variant | Mean return, last 100 | Greedy evaluation | Across-seed std, last 100 | Raw advantage variance |
| --- | ---: | ---: | ---: | ---: |
| Vanilla REINFORCE | 53.27 | 194.70 | 1.88 | 190.75 |
| + Value baseline | 55.76 | 208.42 | 0.33 | 186.93 |

In this small run, the baseline has higher final training and greedy-evaluation returns, lower
across-seed variation, and only a small reduction in raw advantage variance. Three seeds do not
establish a general performance claim. The result also depends on the linear value function, batch
size, and advantage normalization. Unbiasedness is a mathematical property; practical variance
reduction still requires an accurate baseline.

## Why Training and Evaluation Returns Differ

Training samples actions from the policy distribution for exploration. Evaluation always takes the
highest-probability action. A competent greedy policy can therefore coexist with a much lower
stochastic training curve.

## Limitations

- Both the policy and value function are linear.
- This is not Actor-Critic: the baseline waits for complete episodes and uses Monte Carlo returns,
  rather than a bootstrapped TD target.
- The 500-step CartPole time limit is treated as the end of a trajectory.
- Three seeds are suitable for a learning experiment, not a strong statistical conclusion.
