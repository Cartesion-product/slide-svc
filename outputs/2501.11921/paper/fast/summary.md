# Paper Information

**Title**: Goal-oriented Transmission Scheduling: Structure-guided DRL with a Unified Dual On-policy and Off-policy Approach
**Authors**: Jiazheng Chen, Wanchun Liu*

---

# Motivation

以下是基于您提供的文本整理的结构化研究动机：

## 研究问题
**多设备多信道无线通信系统中的面向目标（Goal-oriented）传输调度问题。**
该研究聚焦于在 $N$ 个边缘设备共享 $M$ 个有限衰落信道（$M < N$）的场景下，如何优化调度策略以优先实现应用驱动的目标（如数据新鲜度和系统性能），而非传统的位级准确度。
*   **核心目标：** 寻找最优调度策略 ($\pi$)，以最小化所有设备的长期期望总成本。
*   **具体案例：** 在远程状态估计系统中，这意味着最小化与信息年龄（AoI）直接相关的估计状态均方误差（MSE）。

## 现有方法的局限性
- **传统启发式与动态规划方法：**
    *   **启发式方法（如 Whittle’s Index）：** 虽然计算效率高，但无法保证调度决策的最优性。
    *   **传统动态规划（如值迭代和策略迭代）：** 在现代面向目标的系统中计算上不可行。由于高维状态和动作空间引发的“维度灾难”，即使对于小型系统（如10设备5信道，动作空间超3万个）也难以处理。
- **标准深度强化学习（DRL）算法：**
    *   **离策（Off-Policy）DRL（如 DQN, DDPG）：** 尽管样本效率高，但存在训练不稳定和偏差问题。当前策略与回放缓冲区中旧数据之间的差异会导致训练发散，尤其在大型动态系统中。在 40 设备 20 信道的大规模场景下无法收敛。
    *   **同策（On-Policy）DRL（如 PPO, TRPO）：** 稳定性较好但样本效率极低。每次更新后丢弃数据导致探索不足，使智能体易陷入局部最优。在大规模系统中表现出明显的性能损失。
- **现有的结构增强型 DRL 研究：**
    *   **范围局限：** 大多仅依赖离策 DRL（如 DDPG），继承了其不稳定性，且仅限于小规模系统（通常最多 20 个传感器）。
    *   **缺乏领域深度见解：** 许多应用采用“暴力优化”，未深入研究最优策略的数学性质，导致发现最优解的效率低下。
    *   **理论属性缺失：** 在本研究之前，关于 AoI 状态的最优状态值函数的“渐近凸性”在传输调度领域尚未被探索或证明。

## 研究空白
- **计算可行性与最优性的平衡缺口：** 传统方法要么计算太慢（DP），要么不够精确（启发式），急需一种既能保证性能又能处理大规模问题的方案。
- **DRL 稳定性与效率的权衡缺口：** 现有 DRL 在样本效率（离策）与训练稳定性（同策）之间存在天然矛盾，缺乏能结合两者优点的统一框架。
- **理论导向学习的缺失：** 现有研究缺乏将通信问题的物理特性或数学结构（如单调性、凸性）融入 DRL 训练过程的有效手段。
- **大规模系统的扩展性缺口：** 缺乏能在 40 设备 20 信道等复杂大规模环境下收敛并保持高性能的调度算法。

## 关键挑战
- **高维状态与动作空间：**
    *   **状态空间：** 必须跟踪每个设备的 AoI 和每个设备-信道对的信道状态，随设备数量呈指数级增长。
    *   **动作空间：** 调度器需决定设备与信道的匹配。对于 $N$ 设备 $M$ 信道，动作数为 $N! / (N-M)!$。10设备5信道即产生 30,240 种动作，使传统 MDP 求解器失效。
- **标准 DRL 算法的固有缺陷：** 离策算法的训练不稳定/偏差问题与同策算法的样本低效/易陷入局部最优问题。
- **缺乏领域特定指导：** 若不结合单调性或凸性等结构化属性，单纯依靠“暴力”优化难以在复杂环境中找到理论最优策略。
- **可扩展性压力：** 当系统规模从 20 个传感器扩展到 40 个设备及 20 个信道时，基准算法往往面临不收敛或性能严重下降的挑战。

## 背景背景
- **研究背景：** 随着物联网和远程控制系统的发展，通信目标从单纯的“传输比特”转向“满足特定应用需求”（如 remote state estimation）。
- **技术背景：** 现有的 DRL 虽被用于解决复杂调度，但由于忽略了通信问题的数学结构（如 AoI 的演进规律和信道衰落特性），在效率和可扩展性上遇到瓶颈。
- **创新切入点：** 本研究通过数学证明最优解的结构属性（单调性、渐近凸性、贪婪结构），并以此引导 DRL 训练（SUDO-DRL 算法），旨在弥合理论最优性与实际 DRL 落地之间的鸿沟。

---

# Solution / Methodology

## 框架概述
**SUDO-DRL (Structure-guided Unified Dual On-off policy DRL)** 是一个混合深度强化学习框架，旨在解决大规模目标导向通信系统中的复杂传输调度问题。该框架通过结合 **PPO (Proximal Policy Optimization)** 的在线策略（on-policy）训练稳定性与 **SAC (Soft Actor-Critic)** 的离线策略（off-policy）采样效率，并利用推导出的最优调度策略理论结构属性（单调性、渐近凸性、贪婪结构）来指导神经网络的训练，从而在处理高维状态空间时实现更高的性能和更快的收敛。

## 关键组成部分

1.  **理论结构属性推导 (Theoretical Foundation)**：
    *   作为算法设计的基石，推导了最优解的四个关键属性：V函数的单调性（随AoI和信道状态增加）、V函数的渐近凸性（随AoI状态）、最优策略的单调性（随信道状态）、以及针对共址设备的渐近贪婪结构（高AoI设备强制调度）。

2.  **结构属性评估框架 (Structural Property Evaluation Framework)**：
    *   将理论属性转化为量化指标，用于评分轨迹：
        *   **CM Score (Critic-Monotonicity)**：评估Critic网络是否符合V函数单调性。
        *   **CC Score (Critic-Convexity)**：评估Critic网络是否符合渐近凸性。
        *   **AM Score (Actor-Monotonicity)**：评估Actor网络决策是否符合信道状态单调性。

3.  **统一双损失函数 (Unified Dual Loss Function)**：
    *   **Critic Loss**：结合了当前轨迹的TD误差（在线）和回放池数据的TD误差（离线），并加入结构违反惩罚项（Penalty terms）。
    *   **Actor Loss**：结合了PPO的裁剪损失（在线）与熵正则化损失（离线）。

4.  **结构引导的回放池管理 (Structure-Guided Replay Buffer Management)**：
    *   **选择性存储**：仅存储结构评分（CM, CC, AM）达到或超过历史平均水平的轨迹。
    *   **优先级采样**：基于结构评分和数据新近度（Recency）计算优先级指标进行采样。

5.  **结构引导的预训练 (Structure-Guided Pre-training)**：
    *   利用“渐近贪婪结构”定理，在初始阶段选择强制调度集（高AoI设备）的动作，为模型提供高质量的初始策略。

## 数学表述

### 1. 系统模型与目标
- **目标函数 (Problem 1)**：
  $$\min_{\pi} \lim_{T \to \infty} \mathbb{E}^\pi \left[ \sum_{t=1}^{T} \sum_{n=1}^{N} \gamma^t c_n(\delta_{n,t}) \right]$$
  - $\gamma$：折扣因子 $\in (0,1)$。
  - $c_n(\delta_{n,t})$：基于AoI $\delta$ 的应用特定成本函数。
- **AoI 动态方程 (Eq. 4)**：
  $$\delta_{n,t+1} = \begin{cases} 1, & \text{若传输成功} \\ \delta_{n,t} + 1, & \text{否则} \end{cases}$$
- **信道约束 (Eq. 3)**：
  $$\sum_{n=1}^{N} \mathbb{1}(a_{n,t} = m) = 1, \quad \sum_{m=1}^{M} \mathbb{1}(a_{n,t} = m) \leq 1$$
  - $a_{n,t}$：设备 $n$ 在时间 $t$ 分配的信道。

### 2. 结构属性评分与惩罚
- **Critic 单调性惩罚 (AoI & Channel)**：
  $$\hat{V}_{\mathrm{AoI}} = \max(0, v(\mathbf{s}; \boldsymbol{\nu}) - v(\hat{\mathbf{s}}_{(n)}; \boldsymbol{\nu}))$$
  $$\hat{V}_{\mathrm{Ch}} = \max(0, v(\mathbf{s}; \boldsymbol{\nu}) - v(\hat{\mathbf{s}}_{(n,m)}; \boldsymbol{\nu}))$$
- **Critic 凸性惩罚 (AoI)**：
  $$\check{V}_{\mathrm{AoI}} = \max(0, 2v(\mathbf{s}; \boldsymbol{\nu}) - (v(\check{\mathbf{s}}_{(n)}; \boldsymbol{\nu}) + v(\hat{\mathbf{s}}_{(n)}; \boldsymbol{\nu})))$$
- **Actor 单调性评分**：
  $$\acute{\Lambda}_{\mathrm{Ch},n} = \mathbb{1}(a_n \neq 0 \text{ 且 } a_{\mathrm{Ch},n} \neq a_n)$$

### 3. 统一损失函数
- **Critic 统一损失 (Eq. 22 & 31)**：
  $$L_{\mathrm{SUDO}}(\boldsymbol{\nu}) = L_{\mathrm{On}}(\boldsymbol{\nu}) + \beta_1 L_{\mathrm{Off}}(\boldsymbol{\nu})$$
  $$L_{\mathrm{On}}(\boldsymbol{\nu}) = \frac{1}{B_1} \sum_{l=1}^{B_1} \mathrm{TD}_l^2 + \text{Structural Penalties}$$
- **Actor 统一损失 (Eq. 23 & 38)**：
  $$L_{\mathrm{SUDO}}(\varphi) = L_{\mathrm{On}}(\varphi) + \beta_2 L_{\mathrm{Off}}(\varphi)$$
  $$L_{\mathrm{Off}}(\varphi) = \frac{1}{B_2} \sum_{b=1}^{B_2} \left[ \varpi \log(\pi(\tilde{\mathbf{a}}_b | \mathbf{s}_b; \varphi)) + (c_b + \gamma v(\tilde{\mathbf{s}}_{b+1}; \boldsymbol{\nu})) \right]$$

### 4. 采样优先级 (Eq. 35 & 36)
- **优先级指标**：$p_u = \mathrm{CM}_u + \mathrm{CC}_u + \mathrm{AM}_u$
- **采样概率**：$P_b \triangleq \frac{p_b \cdot \varrho^b}{\sum_{b=1}^R (p_b \cdot \varrho^b)}$
  - $\varrho$：新近度衰减率。

## 技术流程

1.  **初始化**：设置环境参数（$N$ 设备, $M$ 信道）、神经网络权重（Actor $\varphi$, Critic $\nu$）及回放池。
2.  **预训练阶段**：利用定理5（渐近贪婪结构）进行动作选择，收集高质量初始轨迹。
3.  **轨迹采样**：Actor网络与环境交互生成轨迹；若在预训练后，则根据当前策略采样。
4.  **结构评估**：对当前轨迹计算 CM、CC、AM 评分。
5.  **回放池管理**：
    *   对比当前评分与历史平均评分。
    *   若评分优异，则存入回放池并更新优先级指标 $p$。
6.  **损失计算**：
    *   计算在线损失 $L_{On}$（含结构违反惩罚）。
    *   从回放池按优先级采样，计算离线损失 $L_{Off}$。
    *   合并为统一损失 $L_{SUDO}$。
7.  **参数更新**：使用 Adam 优化器更新 $\varphi$ 和 $\nu$。
8.  **重复**：循环执行步骤3-7直至收敛。

## 实现细节

*   **网络结构**：Actor 和 Critic 均为 3 层隐藏层的全连接神经网络。
*   **超参数**：
    *   折扣因子 $\gamma = 0.99$。
    *   PPO 裁剪参数 $\epsilon = 0.2$。
    *   统一损失权重 $\beta_1, \beta_2 = 0.9$。
    *   学习率：Critic = 0.001, Actor = 0.0001。
    *   Batch Size = 128，回放池容量 = 200 轨迹。
*   **信道模型**：i.i.d. 块衰落信道，5 级量化状态，丢包率范围 0.01 至 0.2。
*   **扩展性**：支持多达 40 设备和 20 信道的规模。

## 关键创新

*   **结构引导 (Structure-guided)**：首次将 AoI 调度问题的渐近凸性和单调性等数学证明直接嵌入到 DRL 的损失函数和数据筛选中。
*   **统一双策略 (Unified Dual On-off)**：通过统一损失函数桥接了 PPO 和 SAC，解决了传统离线策略方法在大规模调度中难以收敛的问题。
*   **渐近贪婪预训练**：利用理论发现的最优策略边界情况（定理5）加速冷启动过程，减少 40% 的收敛时间。

---

# Results

## 数据集 / 基准测试
- 姓名：远程状态估计系统仿真环境 (Remote State Estimation System)
- 规模：10,000 训练回合 (Episodes)，每回合 128 步 (Steps)；评估基于 20,000 步的经验模拟。
- 类别/分组：
  - 小规模 (Small-scale)：10 台设备, 5 个信道
  - 中规模 (Medium-scale)：20 台设备, 10 个信道
  - 大规模 (Large-scale)：30 台设备, 15 个信道
  - 超大规模 (Very Large-scale)：40 台设备, 20 个信道
- 其他详情：
  - 状态维度：$N + (N \times M)$，最大输入维度为 840 (40台设备场景)。
  - 信道状态：量化为 $\bar{g} = 5$ 级。
  - 数据包丢弃率：$\{0.2, 0.15, 0.1, 0.05, 0.01\}$。
  - 硬件：Intel Core i7 9700 CPU, 32GB RAM, NVIDIA RTX 3060Ti GPU。

## 评估指标
- Empirical Average Sum MSE Cost：衡量远程估计的平均和均方误差，是目标导向通信的核心指标。
- Convergence Time/Speed：达到稳定成本所需的训练回合数。
- Critic-Monotonicity (CM) Score：衡量 Critic 神经网络是否符合关于信道和 AoI 状态的单调性证明（0-100分）。
- Critic-Convexity (CC) Score：衡量 Critic 神经网络是否符合价值函数关于 AoI 状态的渐进凸性证明（0-100分）。
- Actor-Monotonicity (AM) Score：衡量策略关于信道状态的单调性（0-100分）。
- Success Rate：算法在特定系统规模下是否能成功收敛。

## 主要结果
<table>
<tr><th>Method</th><th>Small (10,5)</th><th>Medium (20,10)</th><th>Large (30,15)</th><th>Very Large (40,20)</th><th>Convergence Speed</th></tr>
<tr><td>DDPG</td><td>Works</td><td>Fails (—)</td><td>Fails (—)</td><td>Fails (—)</td><td>Slow/Unstable</td></tr>
<tr><td>SE-DDPG [21]</td><td>Best Performance</td><td>Works</td><td>Fails (—)</td><td>Fails (—)</td><td>Moderate</td></tr>
<tr><td>MRI-DDPG [22]</td><td>High Performance</td><td>Works</td><td>Fails (—)</td><td>Fails (—)</td><td>Moderate</td></tr>
<tr><td>PPO</td><td>Poor Performance</td><td>Poor Performance</td><td>Works (High Cost)</td><td>Works (High Cost)</td><td>Baseline</td></tr>
<tr><td>SUDO-DRL</td><td>High Performance</td><td>Best Performance</td><td>Best Performance</td><td>Best Performance</td><td>40% Faster than PPO</td></tr>
</table>

## 按类别/分段的表现
<table>
<tr><th>System Scale (N, M)</th><th>Para. Setting</th><th>PPO (MSE Cost)</th><th>SUDO-DRL (MSE Cost)</th><th>Improvement (%)</th></tr>
<tr><td>(10, 5)</td><td>Para. 1</td><td>119.63</td><td>85.52</td><td>~28.5%</td></tr>
<tr><td>(20, 10)</td><td>Para. 5</td><td>569.96</td><td>370.63</td><td>~35%</td></tr>
<tr><td>(30, 15)</td><td>Para. 11</td><td>900.71</td><td>518.03</td><td>~42.5%</td></tr>
<tr><td>(40, 20)</td><td>Para. 14</td><td>971.35</td><td>689.81</td><td>~29%</td></tr>
<tr><td>(40, 20)</td><td>Para. 15</td><td>1291.54</td><td>994.80</td><td>~23%</td></tr>
</table>

## 消融研究
<table>
<tr><th>Variant</th><th>Avg. Sum MSE Cost</th><th>Convergence Time (Episodes)</th><th>Structural Scores (CM/CC/AM)</th></tr>
<tr><td>PPO (Baseline)</td><td>~1000</td><td>Slowest (>5000)</td><td>Low (CC<80, AM<75)</td></tr>
<tr><td>SUDO-DRL (w/o pre-training)</td><td>~700</td><td>~5000</td><td>High (100)</td></tr>
<tr><td>SUDO-DRL (Full)</td><td><700</td><td>~3000 (40% reduction)</td><td>Perfect (100, Faster)</td></tr>
</table>

## 详细发现
- 系统性能提升：SUDO-DRL 相比 PPO 基准算法，将系统性能（MSE 成本）提升了 25% 至 45%。
- 收敛效率：通过结构引导的预训练阶段，收敛时间缩短了约 40%。
- 可扩展性突破：SUDO-DRL 成功处理了 40 个设备和 20 个信道的规模，而所有离策 (Off-policy) 基准算法（DDPG, SE-DDPG, MRI-DDPG）在此规模下均无法收敛。
- 结构一致性：SUDO-DRL 在 200 回合内即可达到 100 分的 Critic 凸性 (CC) 评分，而 PPO 始终低于 80 分。
- 预训练增益：全功能 SUDO-DRL 的初始成本从约 800 开始，远低于无预训练版本的起始点。

## 比较分析
- 相比 PPO：PPO 虽然具有稳定性，但在高维空间中由于缺乏结构引导，性能显著落后于 SUDO-DRL（成本高出 25%-40%）。
- 相比 DDPG 变体：在小规模（10, 5）下，SE-DDPG 等离策方法由于采样效率极高表现略优，但随着规模扩大，这些方法因无法处理高维动作空间而彻底失效，而 SUDO-DRL 通过统一的双策 (Dual On-off policy) 架构兼顾了稳定性和效率。

## 主要贡献
1. 理论证明的结构属性：首次证明了最优价值函数关于 AoI 状态具有渐进凸性 (Asymptotic Convexity)，并证明了关于信道和 AoI 状态的单调性。
2. SUDO-DRL 算法框架：提出了一种结构引导的统一双策深度强化学习方法，结合了在策 (On-policy) 的稳定性和离策 (Off-policy) 的样本效率。
3. 结构引导的数据存储方案：设计了一种基于结构评分的经验回放机制，仅存储符合理论属性的高质量轨迹。
4. 渐进贪婪预训练：利用理论推导出的渐进贪婪结构（Theorem 5）进行策略初始化，显著加速了学习过程。

## 新奇与创新
- 凸性属性的应用：以往工作仅关注单调性，本文首次将渐进凸性引入传输调度 DRL 的结构引导中。
- 统一损失函数：不同于传统的混合方法，本文使用统一的损失函数整合了 PPO 的稳定性和 SAC 的样本效率。
- 结构评分系统：引入了 CM、CC 和 AM 三种评分指标，量化神经网络对数学结构的遵循程度，并将其直接用于数据筛选。

## 局限性
- 线性系统假设：实验主要基于线性时不变 (LTI) 系统模型，对于高度非线性的动态过程可能需要进一步验证。
- 状态量化：信道状态被量化为 5 级，在连续信道状态下的表现尚未深入探讨。

## 未来方向
- 非线性代价函数：探索 SUDO-DRL 在更复杂的非线性目标函数下的适用性。
- 分布式实现：研究如何将该集中式调度框架扩展到分布式边缘计算场景。

## 更广泛的影响
- 目标导向通信：该研究为 6G 网络中的目标导向 (Goal-oriented) 和语义通信提供了高效的资源调度方案，尤其是在大规模物联网 (IoT) 监测和远程控制领域具有应用潜力。