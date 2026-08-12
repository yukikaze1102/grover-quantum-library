# Grover's Algorithm — Quantum Library

量子计算课程 Presentation 配套 Demo：**Grover 多条目搜索（Multi-Item Search）**，
场景包装为「在 512 本藏书里找到阅读清单上的 2 本书」。

> Presentation 全英文，时长 ~5 分钟。结构：Grover 数学 → 程序实现 → 物理量子计算机。

---

## 1. 场景与参数

| 参数 | 值 | 说明 |
|---|---|---|
| 搜索空间 N | **512** | 2⁹，9 个 qubit 编码 512 个书架位（书号） |
| 目标书 M | **2** | 书 #42 和 书 #137（多条目搜索） |
| 迭代次数 k | **12** | `k ≈ (π/4)·√(N/M) ≈ 12.6`，精确最优值 12 |

- 书 #42  = `000101010` — "Quantum Computing: A Gentle Introduction"
- 书 #137 = `010001001` — "Quantum Field Theory"（精细结构常数 1/137 的彩蛋）

**关键公式**

```
k_opt = round((π/2 − θ) / 2θ),    θ = arcsin(√(M/N))
```

---

## 2. 文件结构

```
├── grover_512_library.py      # 主程序：构建并运行 Grover 电路，打印结果（512 版本，模拟器）
├── make_figures.py            # 生成三张演示用图
├── grover_circuit.png         # 电路图（1 次迭代的真实电路，实际运行 12 次）
├── grover_results.png         # 结果直方图（512 本书的测量概率）
├── grover_amplification.png   # 分析图：命中概率 vs 迭代次数 P(k)
├── grover_hardware.py         # 真机对比脚本（8-item，模拟器 vs 真实量子硬件）
├── hardware_vs_simulator.png  # 真机 vs 模拟器对比图
└── README.md
```

---

## 3. 环境要求

- Python ≥ 3.10
- `qiskit` ≥ 2.x，`qiskit-aer`
- 绘图可选：`matplotlib`、`pylatexenc`（Qiskit mpl 电路图需要）
- 真机运行：`qiskit-ibm-runtime`（可选，离线用假设备则不需要）

```bash
pip install qiskit qiskit-aer matplotlib pylatexenc qiskit-ibm-runtime
```

---

## 4. 运行

```bash
# 运行算法，输出测量结果
python grover_512_library.py

# 生成三张图（会重新跑一次仿真，约 10~15 秒）
python make_figures.py
```

**预期输出（grover_512_library.py）**

```
N = 512 books, M = 2 targets, k = 12 Grover iterations

counts: {'000101010': 509, '010001001': 515}

Top results:
  010001001 :  515 shots (50.29%)  <-- marked
  000101010 :  509 shots (49.71%)  <-- marked

Total probability on the 2 marked books: 100.00%
All 510 unmarked books combined:      0.00%
```

> 每次运行结果在 ±20 左右浮动，但两本目标书总和始终 ≈ 100%。需要精确复现可加
> `seed_simulator=42`（`make_figures.py` 已默认使用）。

---

## 4.5 真机运行（Slide 5 素材）

`grover_hardware.py` 把 8-item（N=8, M=2, k=1）Grover 电路跑在三种方式上并出对比图
`hardware_vs_simulator.png`：

| 方式 | 说明 |
|---|---|
| Ideal（模拟器） | 无噪声，目标书各 ~50%（合计 100%） |
| 原始设备噪声 | Aer + 设备噪声模型，**不做误差缓解**（目标书合计 ~85%） |
| 真机 + 缓解 | Qiskit Runtime `SamplerV2`（内置测量误差缓解） |

```bash
# 离线演示（无 token 时自动回退到 FakeBrisbane 噪声模型，可直接跑）
python grover_hardware.py

# 跑真实 IBM 量子硬件（需要免费账号 token）
IBM_QUANTUM_TOKEN=xxxxxxxx python grover_hardware.py
# 可选指定后端：IBM_BACKEND=ibm_brisbane
```

**获取 token**：在 [IBM Quantum Platform](https://quantum.ibm.com/) 注册免费账号 →
Dashboard → API token（勾选 Access **Real time** systems）。

> 8-item 电路只有 18 个 CNOT，深度 35，远在相干时间内，真机跑得动；
> 512-item 电路 9,072 个 CNOT 则超出现役芯片能力——这就是 Slide 5 的论点：
> **"qubits are cheap, depth is the bottleneck."**

---

## 5. 算法速览（对应 PPT 数学段）

1. **Superposition**：`H` 门把 9 个 qubit 制备到 512 个态的均匀叠加，一次"覆盖"整个书架。
2. **Oracle（超能图书管理员）**：对目标书翻相位 `|x⟩ → −|x⟩`，即用多受控 Z 门标记答案。
3. **Diffusion（均值反演）**：把所有振幅绕平均值翻转，目标书的振幅被逐轮放大。
4. 重复 k=12 轮后测量：目标书各 ~50%，其余 ≈ 0。

---

## 6. 演示要点（Presentation Notes）

| Slide | 台词要点（英文） |
|---|---|
| Hook | "512 books, 2 on your list. Up to 512 tries. Grover: 12 queries." |
| Oracle | "A super-librarian: one glance, it stamps the match with a minus sign." |
| Multi-item | "Real searches rarely return one book — the formula handles any M: k ≈ (π/4)√(N/M)." |
| Demo | "9 bits = 512 shelf addresses. Query all at once, amplify 12 times." |
| Hardware | "512 books needs thousands of CNOTs — too deep for today's chips. On real hardware we search just 8 books." |

---

## 7. 备注

- **多受控门需要 transpile**：`ZGate().control(8)`（c9z）不是 Aer 的基础门，必须先用
  `transpile(qc, sim)` 分解后再运行，否则报 `unknown instruction: c8z`。
- **Qiskit counts 是 MSB-first（大端）**：代码里 marked 字符串按大端书写，直接与打印结果对应。
- 真机（IBM Quantum）只能跑小规模版本（如 N=8, M=2, k=1），因为 512 规模电路的
  CNOT 深度远超当前芯片相干时间——这本身就是 Slide 5 的论点：
  *"Depth, not qubit count, is the real bottleneck."*

---

## 8. 参考资料

- L. K. Grover, *A fast quantum mechanical algorithm for database search*, STOC 1996.
- Nielsen & Chuang, *Quantum Computation and Quantum Information*, Ch. 6.
- IBM Quantum / Qiskit documentation.
