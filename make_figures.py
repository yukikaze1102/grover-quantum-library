"""
Generate the three figures for the Grover 512-book presentation:
  1. grover_circuit.png        — quantum circuit, one of k=12 identical iterations
  2. grover_results.png        — measurement histogram over all 512 books
  3. grover_amplification.png  — success probability vs #iterations (analysis curve)
Uses the dataviz palette (light surface) from the reference instance.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import ZGate
from qiskit_aer import AerSimulator

# ---------------- palette (light surface, from dataviz reference) ----------------
SURFACE  = "#fcfcfb"
INK      = "#0b0b0b"
SECOND   = "#52514e"
MUTED    = "#898781"
GRID     = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE     = "#2a78d6"   # categorical slot 1
ORANGE   = "#eb6834"   # categorical slot 2 (accent / "found")
LINEW    = 2.0

# ---------------- problem parameters (same as grover_512_library.py) ----------------
N      = 512
n      = int(np.log2(N))
marked = ["000101010", "010001001"]        # book #42, book #137 (MSB first)
M      = len(marked)
theta  = np.arcsin(np.sqrt(M / N))
k_opt  = int(np.round((np.pi / 2 - theta) / (2 * theta)))     # = 12

marked_idx = [int(b, 2) for b in marked]                      # [42, 137]


def build_circuit(iterations, measure=False):
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    MCZ = ZGate().control(n - 1)

    def oracle(qc):
        for bits in marked:
            for i, b in enumerate(bits):
                if b == "0":
                    qc.x(qr[n - 1 - i])
            qc.append(MCZ, qr)
            for i, b in enumerate(bits):
                if b == "0":
                    qc.x(qr[n - 1 - i])

    def diffusion(qc):
        qc.h(qr); qc.x(qr)
        qc.append(MCZ, qr)
        qc.x(qr); qc.h(qr)

    qc.h(qr)
    for _ in range(iterations):
        oracle(qc); diffusion(qc)
    if measure:
        qc.measure(qr, cr)
    return qc


# ==================== Figure 1 — circuit diagram (one iteration) ====================
qc_iter = build_circuit(1)
style = {"backgroundcolor": SURFACE}
circ_fig = qc_iter.draw(
    output="mpl", style=style, fold=80, scale=0.72, idle_wires=False,
)
circ_fig.axes[0].set_title(
    f"Grover circuit — one of k = {k_opt} identical iterations\n"
    f"Oracle = super-librarian marks books #42 & #137  |  N = {N}, M = {M}",
    fontsize=11, color=INK, pad=14,
)
circ_fig.savefig("grover_circuit.png", dpi=200, bbox_inches="tight",
                 facecolor=SURFACE)
plt.close(circ_fig)

# ==================== Figure 2 — measurement histogram ====================
qc_full = build_circuit(k_opt, measure=True)
sim = AerSimulator()
tqc = transpile(qc_full, sim)
counts = sim.run(tqc, shots=1024, seed_simulator=42).result().get_counts()

total = sum(counts.values())
probs = np.zeros(N)
for key, c in counts.items():
    probs[int(key, 2)] = c / total

fig, ax = plt.subplots(figsize=(9.2, 4.4), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

x = np.arange(N)
colors = np.full(N, GRID)
colors[marked_idx] = ORANGE
ax.bar(x, probs, color=colors, width=1.0)

# annotation of the two hits
for idx, name in zip(marked_idx, ["#42  (Quantum Computing:\n        A Gentle Introduction)",
                                  "#137 (Quantum Field Theory)"]):
    ax.annotate(f"{100*probs[idx]:.1f}%", (idx, probs[idx]),
                xytext=(0, 7), textcoords="offset points",
                ha="center", fontsize=10, color=ORANGE, fontweight="bold")

ax.text(511, 0.96, "other 510 books: 0.00% combined",
        ha="right", va="top", fontsize=9.5, color=SECOND)

ax.set_xlim(-5, 516)
ax.set_ylim(0, 1.04)
ax.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax.set_xticks([0, 42, 137, 511])
ax.set_xticklabels(["0", "#42", "#137", "511"])
ax.tick_params(axis="both", colors=MUTED, labelsize=9)
for spine in ax.spines.values():
    spine.set_color(BASELINE)
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)

ax.set_title("Grover search over 512 books — 12 queries, both answers found",
             fontsize=12.5, color=INK, pad=12)
ax.set_xlabel("book call number (512 shelves)", fontsize=10, color=SECOND)
ax.set_ylabel("measurement probability", fontsize=10, color=SECOND)

fig.tight_layout()
fig.savefig("grover_results.png", dpi=200, bbox_inches="tight", facecolor=SURFACE)
plt.close(fig)

# ==================== Figure 3 — amplification analysis curve ====================
ks = np.arange(0, 26)
P = np.sin((2 * ks + 1) * theta) ** 2                      # theory
P_meas = probs[marked_idx].sum()                            # measured at k_opt

fig, ax = plt.subplots(figsize=(8.6, 4.4), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ax.plot(ks, P, color=BLUE, linewidth=LINEW, zorder=3)

# chosen iteration point + measured result
ax.axvline(k_opt, color=MUTED, linewidth=1.0, linestyle="--", zorder=1)
ax.plot(k_opt, P[k_opt], "o", markersize=9, color=BLUE, zorder=4,
        markeredgecolor=SURFACE, markeredgewidth=2)
ax.plot(k_opt, P_meas, "*", markersize=15, color=ORANGE, zorder=5,
        markeredgecolor=SURFACE, markeredgewidth=1.5)

ax.annotate(f"k = {k_opt}:  theory {100*P[k_opt]:.1f}%   measured {100*P_meas:.1f}%",
            (k_opt, P[k_opt]), xytext=(0, -11), textcoords="offset points",
            ha="center", va="top", fontsize=10, color=INK, fontweight="bold")
ax.annotate("too few iterations:\nanswers still diluted",
            (3, P[3]), xytext=(1.2, 0.62), fontsize=8.5, color=SECOND,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
ax.annotate("too many iterations:\nprobability decays (sin² oscillation)",
            (23, P[23]), xytext=(16.5, 0.18), fontsize=8.5, color=SECOND,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))

ax.set_xlim(0, 25)
ax.set_ylim(0, 1.03)
ax.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax.tick_params(axis="both", colors=MUTED, labelsize=9)
for spine in ax.spines.values():
    spine.set_color(BASELINE)
ax.grid(axis="both", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)

ax.set_title(r"Amplitude amplification — success probability vs iterations" + "\n"
             r"$P(k) = \sin^2\left((2k+1)\,\theta\right),\ \theta=\arcsin\sqrt{M/N}$",
             fontsize=12, color=INK, pad=10)
ax.set_xlabel("number of Grover iterations  k", fontsize=10, color=SECOND)
ax.set_ylabel("probability of finding a marked book", fontsize=10, color=SECOND)

fig.tight_layout()
fig.savefig("grover_amplification.png", dpi=200, bbox_inches="tight",
            facecolor=SURFACE)
plt.close(fig)

print("Saved: grover_circuit.png, grover_results.png, grover_amplification.png")
print(f"counts: {counts}")
print(f"k_opt = {k_opt}, measured P(marked) = {100*P_meas:.2f}%")
