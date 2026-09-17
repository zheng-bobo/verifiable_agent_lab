# 第一周：GridWorld 基线

[English](README.md) | [简体中文](README.zh-CN.md)

本实验验证后续 Agent harness 所需的经典强化学习基础：

- 确定性 GridWorld 环境
- 已知环境转移模型时的 Value Iteration
- 不依赖环境模型的表格型 Q-learning
- 三个固定 epsilon 下的 epsilon-greedy 探索

## 运行方式

在仓库根目录执行：

```bash
python experiments/week01-gridworld/run.py
```

该命令使用固定随机种子重新生成 `results.json`。

## 环境

```text
S . . .
. # . .
. . # .
. . . G
```

- 普通步骤奖励：`-1`
- 进入终点奖励：`+10`
- 每轮最多 50 步
- 最优路线：6 步，总奖励为 `5`

## 实验问题

1. Value Iteration 能否找到 6 步的最优策略？
2. Q-learning 能否在不知道环境转移模型的情况下找到相同路径？
3. 固定 epsilon 如何影响训练早期和后期的回报？

## 结果解释

`results.json` 分别记录学习后 greedy policy 的评测，以及训练前 100 和后 100 个 episode 的平均
回报。Greedy evaluation 与带探索的训练回报相互分离，避免把探索成本误认为策略质量。
