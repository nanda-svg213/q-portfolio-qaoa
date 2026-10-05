import unittest
import numpy as np
try:
    import qiskit
    from qiskit.quantum_info import Statevector
except ImportError:
    qiskit = None
from quantum.portfolio import default_problem, qubo, energies
from quantum.qaoa_sim import qaoa_state


@unittest.skipIf(qiskit is None, "qiskit not installed")
class QiskitMatchesNumpy(unittest.TestCase):
    def test_circuit_statevector_equals_reference(self):
        from quantum.circuit import build_circuit
        p = default_problem(3)
        g, b = [0.4, 0.9], [0.7, 0.3]
        sv = Statevector.from_instruction(build_circuit(p, g, b)).data
        ref = qaoa_state(energies(*qubo(p, False), p.n), p.n, p.k, g, b)
        self.assertAlmostEqual(abs(np.vdot(sv, ref)), 1.0, places=8)  # equal up to global phase

    def test_routing_metrics_are_real(self):
        from quantum.circuit import build_circuit
        from quantum.heavy_hex import route_with_qiskit
        qc = build_circuit(default_problem(3), [0.4], [0.7])
        routed, m = route_with_qiskit(qc)
        self.assertGreaterEqual(m["cx_after"], m["cx_before"])
        self.assertEqual(routed.num_qubits, m["physical_qubits_available"])
