"""Qiskit QAOA circuit with XY mixer. Mirrors quantum/qaoa_sim.py gate for gate."""
from .portfolio import Problem, qubo, ising
from .qaoa_sim import mixer_layers


def build_circuit(p: Problem, gammas, betas):
    from qiskit import QuantumCircuit
    n = p.n
    Q, off = qubo(p, with_penalty=False)
    h, J, _ = ising(Q, off)
    qc = QuantumCircuit(n)
    from qiskit.circuit.library import StatePreparation
    from .qaoa_sim import initial_state
    qc.append(StatePreparation(initial_state(n, p.k)), range(n))   # Dicke state, weight k
    for g, b in zip(gammas, betas):
        for i in range(n):
            qc.rz(2 * g * h[i], i)                # exp(-i g h Z)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(J[i, j]) > 1e-12:
                    qc.rzz(2 * g * J[i, j], i, j)
        for layer in mixer_layers(n):
            for (i, j) in layer:
                qc.rxx(2 * b, i, j)               # exp(-i b (XX+YY)) = RXX(2b) RYY(2b)
                qc.ryy(2 * b, i, j)
    return qc
