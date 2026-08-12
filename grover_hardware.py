"""
Grover on (nearly) real quantum hardware — 8-item toy version
==============================================================
Compares three ways of running the SAME 8-book Grover circuit:
  1. Ideal simulator          — noiseless, the textbook answer
  2. Raw device noise         — circuit + the device's error model (no mitigation)
  3. Real device (mitigated)  — run on a real IBM backend via Qiskit Runtime
                               (SamplerV2 applies measurement error mitigation by default)

Problem: N = 8 books, M = 2 targets (books #5 and #6), k = 1 Grover iteration.

Run on a real device:      IBM_QUANTUM_TOKEN=... python grover_hardware.py
Offline (no token):        python grover_hardware.py
                           -> falls back to FakeBrisbane (offline noise model)
Optional backend override: IBM_BACKEND=ibm_brisbane
Output: hardware_vs_simulator.png
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit.library import ZGate
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeBrisbane

# ---------- palette (light surface) ----------
SURFACE, INK, SECOND, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # categorical 1/2/3

SHOTS = 8192

# ---------- problem ----------
N, marked = 8, ["101", "110"]           # books #5 and #6 (MSB first), M = 2, k = 1
M = len(marked)
marked_idx = [int(b, 2) for b in marked]


def build_grover(N, marked):
    n = int(np.log2(N))
    qr, cr = QuantumRegister(n, "q"), ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    MCZ = ZGate().control(n - 1)

    def oracle():
        for bits in marked:
            for i, b in enumerate(bits):
                if b == "0":
                    qc.x(qr[n - 1 - i])
            qc.append(MCZ, qr)
            for i, b in enumerate(bits):
                if b == "0":
                    qc.x(qr[n - 1 - i])

    def diffusion():
        qc.h(qr); qc.x(qr)
        qc.append(MCZ, qr)
        qc.x(qr); qc.h(qr)

    qc.h(qr)
    oracle(); diffusion()                 # k = 1 iteration (optimum for N=8, M=2)
    qc.measure(qr, cr)
    return qc


def probs_of(counts, N):
    total = sum(counts.values())
    p = np.zeros(N)
    for key, c in counts.items():
        p[int(key, 2)] = c / total
    return p


# ---------- backend selection ----------
token = os.environ.get("IBM_QUANTUM_TOKEN")
backend_name = os.environ.get("IBM_BACKEND", "ibm_brisbane")

if token:
    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitRuntimeService(channel="ibm_quantum", token=token)
    try:
        backend = service.backend(backend_name)
    except Exception:
        backend = service.least_busy(operational=True, min_num_qubits=3)
    mode_label = f"REAL backend: {backend.name}"
else:
    backend = FakeBrisbane()
    mode_label = f"OFFLINE fake backend (noise model of {backend.name})"
print(f"[mode] {mode_label}")

qc = build_grover(N, marked)
isa = transpile(qc, backend=backend, optimization_level=3)

# ---------- 1. ideal simulator ----------
ideal_p = probs_of(
    AerSimulator().run(transpile(qc, AerSimulator()), shots=SHOTS, seed_simulator=42)
    .result().get_counts(), N)

# ---------- 2. raw device noise (Aer + backend noise model, no mitigation) ----------
try:
    noise = NoiseModel.from_backend(backend)
    raw_p = probs_of(
        AerSimulator(noise_model=noise).run(isa, shots=SHOTS, seed_simulator=42)
        .result().get_counts(), N)
except Exception as e:
    print(f"[warn] raw-noise reference skipped: {e}")
    raw_p = None

# ---------- 3. real device via SamplerV2 (built-in measurement error mitigation) ----------
sampler = SamplerV2(mode=backend)
hw_p = probs_of(
    sampler.run([isa], shots=SHOTS).result()[0].data.c.get_counts(), N)

# ---------- summary ----------
def hit(p):
    return p[marked_idx].sum() if p is not None else float("nan")

print(f"\nProbability on the two marked books:")
print(f"  ideal               : {100*hit(ideal_p):5.2f}%")
print(f"  raw device noise    : {100*hit(raw_p):5.2f}%")
print(f"  device + mitigation : {100*hit(hw_p):5.2f}%")

if raw_p is None:
    raw_p = np.zeros(N)

# ---------- figure ----------
states = [f"{i:03b}" for i in range(N)]
x = np.arange(N)
w = 0.26

fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ax.bar(x - w, ideal_p, width=w, color=BLUE,  label="Ideal (simulator)")
ax.bar(x,     raw_p,  width=w, color=ORANGE, label="Device + raw noise")
ax.bar(x + w, hw_p,   width=w, color=AQUA,   label="Device + error mitigation")

# shade the two marked books
for idx in marked_idx:
    ax.axvspan(idx - 1.5 * w, idx + 1.5 * w, color=GRID, alpha=0.6, zorder=0)
ax.text(0.0, 0.96, "marked books: #5 (101) and #6 (110)",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=9.5, color=INK, fontweight="bold")

ax.set_ylim(0, 1.05)
ax.set_yticks([0, 0.25, 0.50, 0.75, 1.00])
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
ax.set_xticks(x)
ax.set_xticklabels(states, fontsize=9)
for label, idx in zip(ax.get_xticklabels(), x):
    label.set_color(ORANGE if idx in marked_idx else MUTED)
ax.set_xlabel("book call number (3 bits)", fontsize=10, color=SECOND)
ax.set_ylabel("measurement probability", fontsize=10, color=SECOND)
ax.legend(frameon=False, fontsize=9, loc="upper right")
for spine in ax.spines.values():
    spine.set_color(BASELINE)
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
ax.tick_params(axis="both", colors=MUTED, labelsize=9)

ax.set_title("Grover on 8 books — ideal simulator vs real quantum hardware\n"
             f"mode: {mode_label}   (N = {N}, M = {M}, k = 1, {SHOTS} shots)",
             fontsize=12, color=INK, pad=26)

fig.tight_layout()
fig.savefig("hardware_vs_simulator.png", dpi=200, bbox_inches="tight", facecolor=SURFACE)
print("\nSaved: hardware_vs_simulator.png")
