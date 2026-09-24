# 第三周：从零实现 REINFORCE 与 Value Baseline

[English](README.md) | [简体中文](README.zh-CN.md)

本实验在 `CartPole-v1` 上对比：

1. 原始 REINFORCE：用 Monte Carlo reward-to-go 直接更新策略。
2. REINFORCE + value baseline：用 `G_t - V(s_t)` 更新策略，并用回报监督训练
   `V(s)`。

策略、return、baseline、梯度和 Adam 更新全部使用 NumPy 从零实现。Gymnasium 只提供环境，
没有使用 PyTorch、JAX、Stable-Baselines3 或自动微分。

## 安装与运行

在仓库根目录执行：

```bash
python -m pip install -e ".[dev,rl]"
python experiments/week03-reinforce/run.py
```

快速检查：

```bash
python experiments/week03-reinforce/run.py \
  --episodes 50 \
  --seeds 7 \
  --evaluation-episodes 5 \
  --output /tmp/reinforce-smoke.json \
  --plot /tmp/reinforce-smoke.svg
```

默认实验使用三个随机种子，各训练 500 个 episode，生成：

- `results.json`：配置、逐 seed 指标、聚合结果和模型参数。
- `learning-curves.svg`：两种方法的 25-episode 平滑训练曲线。

CartPole 有四维 observation 和两个离散 action；每存活一步得到 `+1`，`v1` 最多运行 500
步。环境定义见 [Gymnasium CartPole 文档](https://gymnasium.farama.org/environments/classic_control/cart_pole/)。

## 代码阅读顺序

1. `discounted_returns()`：反向计算每一步的 reward-to-go。
2. `SoftmaxPolicy.probabilities()`：把线性 logits 转换为 action 概率。
3. `SoftmaxPolicy.update()`：显式计算 `∇ log π(a|s)` 并做梯度上升。
4. `LinearValueBaseline`：用均方误差拟合 `V(s)`。
5. `train_reinforce()`：采样轨迹、组 batch、计算 advantage、更新策略和 baseline。
6. `experiments/week03-reinforce/run.py`：多随机种子对照与确定性 greedy 评测。

核心实现位于：

```text
src/verifiable_agent_lab/rl/reinforce.py
```

## 1. Vanilla REINFORCE

每一步使用 reward-to-go：

```text
G_t = r_t + γr_{t+1} + γ²r_{t+2} + ...
```

策略梯度的 Monte Carlo 估计为：

```text
∇J(θ) ≈ Σ_t G_t ∇ log πθ(a_t | s_t)
```

对于 softmax policy，代码直接构造 score-function gradient：

```text
∂ log π(a|s) / ∂ logits = one_hot(a) - π(.|s)
```

## 2. Value Baseline

带 baseline 时使用：

```text
A_t = G_t - Vφ(s_t)
∇J(θ) ≈ Σ_t A_t ∇ log πθ(a_t | s_t)
```

`Vφ(s)` 只接收 state，不接收本次 action。对于任意只依赖 state 的 baseline：

```text
E_a[b(s) ∇ log π(a|s)]
= b(s) Σ_a π(a|s) ∇ log π(a|s)
= b(s) ∇ Σ_a π(a|s)
= b(s) ∇1
= 0
```

因此它不会改变 policy gradient 的期望；如果 `V(s)` 能预测回报，就可能降低 Monte Carlo
估计的方差。Baseline 通过下面的回归目标学习：

```text
L_value = mean((Vφ(s_t) - G_t)²)
```

本实验先使用更新前的 `V(s)` 计算 advantage，再拟合当前 batch 的 returns。

## 3. 为什么两组都标准化 Advantage

默认配置会在每个 batch 内将用于策略更新的 advantage 标准化。这能避免 CartPole 中 episode
变长时梯度尺度随 return 一起快速放大。为了仍能观察 baseline 的作用，
`mean_raw_advantage_variance` 记录的是标准化之前的原始 advantage 方差。

这意味着实验比较的是“相同数值稳定措施下，有无 state-value baseline”，而不是把
normalization 也作为实验变量。上面的无偏性推导针对未经标准化的 state-only baseline；
使用当前 batch 的样本均值和方差做 normalization 是额外的实用启发式，会引入有限样本效应。

## 默认结果

仓库中的 `results.json` 由 `7、42、329` 三个 seed 生成：

| 方法 | 最后 100 轮平均回报 | Greedy 评测回报 | seed 间最后 100 轮标准差 | 原始 advantage 方差 |
| --- | ---: | ---: | ---: | ---: |
| Vanilla REINFORCE | 53.27 | 194.70 | 1.88 | 190.75 |
| + Value baseline | 55.76 | 208.42 | 0.33 | 186.93 |

在这次小样本实验中，baseline 的最终训练回报和 greedy 评测回报较高，seed 间差异较小，原始
advantage 方差只小幅下降。三个 seed 不能证明 baseline 一定更好；结果还受到线性 value
function 表达能力、batch 大小和 advantage normalization 影响。这个限制本身很重要：
**baseline 的无偏性是数学性质，但实际降方差效果取决于 baseline 是否学得足够准确。**

## 训练回报与 Greedy 评测为什么不同

训练时 action 来自 policy 分布采样，用于探索；评测时始终选择概率最高的 action。因此即使
greedy policy 已能保持平衡，训练曲线仍会因为随机 action 明显更低。不能把 stochastic
training return 与 deterministic evaluation return 混为同一个指标。

## 已知限制

- 策略和 value function 都是线性模型，没有隐藏层。
- baseline 不是 Actor-Critic：它仍然等待完整 episode 后使用 Monte Carlo return，不做
  TD bootstrap。
- CartPole 的 500 步 time limit 被视为一次轨迹结束。
- 三个 seed 只适合学习实验；正式统计结论需要更多 seed 和置信区间。
