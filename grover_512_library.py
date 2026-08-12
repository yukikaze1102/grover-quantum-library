"""
Grover's Algorithm — Quantum Library: find 2 books among 512.
===============================================================
Scenario : a library with 512 books, each with a 9-bit call number.
Query    : find the 2 books on your reading list.
Oracle   : a "super-librarian" that phase-flips the matching books.
Speed-up : k ~= (pi/4)*sqrt(N/M) ~= 12.6  ->  k = 12 queries,
           vs up to 512 (avg 256) by checking book by book.

The two target books:
  #42  ->  000101010   "Quantum Computing: A Gentle Introduction"
  #137 ->  010001001   "Quantum Field Theory"   (the fine-structure constant ~ 1/137)
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import ZGate
from qiskit_aer import AerSimulator

N      = 512                        # number of books
n      = int(np.log2(N))            # 9 qubits -> 2^9 = 512 shelf addresses
marked = ['000101010', '010001001'] # book #42 and book #137 (MSB first)
M      = len(marked)

# Optimal number of Grover iterations (exact form):
theta = np.arcsin(np.sqrt(M / N))                       # rotation per iteration
k = int(np.round((np.pi / 2 - theta) / (2 * theta)))    # = 12
# textbook shortcut:  k ~= (pi/4)*sqrt(N/M) ~= 12.6  ->  also 12

qr = QuantumRegister(n, 'q')
cr = ClassicalRegister(n, 'c')
qc = QuantumCircuit(qr, cr)
MCZ = ZGate().control(n - 1)        # n-qubit controlled-Z: flips phase of |11..1>


def oracle(qc, marked):
    """Super-librarian: phase-flip every matching book."""
    for bits in marked:
        for i, b in enumerate(bits):          # bits = q_{n-1}..q_0 (MSB first)
            if b == '0':
                qc.x(qr[n - 1 - i])           # map the book onto |11..1>
        qc.append(MCZ, qr)
        for i, b in enumerate(bits):
            if b == '0':
                qc.x(qr[n - 1 - i])


def diffusion(qc):
    """Amplify the marked amplitudes (inversion about the mean)."""
    qc.h(qr)
    qc.x(qr)
    qc.append(MCZ, qr)
    qc.x(qr)
    qc.h(qr)


# uniform superposition over all 512 books
qc.h(qr)

# k Grover iterations
for _ in range(k):
    oracle(qc, marked)
    diffusion(qc)

qc.measure(qr, cr)

# run on the simulator (transpile multi-controlled gates to Aer's basis set first)
from qiskit import transpile

sim = AerSimulator()
tqc = transpile(qc, sim)
counts = sim.run(tqc, shots=1024).result().get_counts()

total = sum(counts.values())
print(f"N = {N} books, M = {M} targets, k = {k} Grover iterations\n")
print("counts:", counts)
print("\nTop results:")
for s, c in sorted(counts.items(), key=lambda kv: -kv[1])[:5]:
    tag = "  <-- marked" if s in marked else ""
    print(f"  {s} : {c:4d} shots ({100*c/total:5.2f}%){tag}")

hit = sum(c for s, c in counts.items() if s in marked)
print(f"\nTotal probability on the 2 marked books: {100*hit/total:.2f}%")
print(f"All {N - M} unmarked books combined:      {100*(1-hit/total):.2f}%")
