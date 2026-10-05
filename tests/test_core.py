import itertools, unittest
import numpy as np
from quantum.portfolio import *
from quantum.qaoa_sim import *
from quantum.heavy_hex import heavy_hex_edges


class Core(unittest.TestCase):
    def setUp(self):
        self.p = default_problem(3)
        self.p.penalty = 2.0

    def test_qubo_matches_objective_on_feasible(self):
        Q, off = qubo(self.p, with_penalty=False)
        for s in range(2 ** self.p.n):
            x = bits(s, self.p.n)
            self.assertAlmostEqual(qubo_value(Q, off, x), objective(self.p, x))

    def test_penalty_zero_iff_feasible(self):
        Qp, offp = qubo(self.p)
        Q, off = qubo(self.p, with_penalty=False)
        for s in range(2 ** self.p.n):
            x = bits(s, self.p.n)
            extra = qubo_value(Qp, offp, x) - qubo_value(Q, off, x)
            self.assertAlmostEqual(extra, self.p.penalty * (x.sum() - self.p.k) ** 2)

    def test_ising_equals_qubo(self):
        Q, off = qubo(self.p)
        h, J, c = ising(Q, off)
        for s in range(2 ** self.p.n):
            x = bits(s, self.p.n)
            self.assertAlmostEqual(ising_value(h, J, c, x), qubo_value(Q, off, x))

    def test_brute_force_is_global_feasible_min(self):
        bf = brute_force(self.p)
        feas = [objective(self.p, bits(s, 6)) for s in range(64) if bits(s, 6).sum() == 3]
        self.assertAlmostEqual(bf["objective"], min(feas))

    def test_xy_mixer_preserves_hamming_weight_and_norm(self):
        n, k = 6, 3
        cost = energies(*qubo(self.p, with_penalty=False), n)
        psi = qaoa_state(cost, n, k, [0.4, 0.9], [0.7, 0.3])
        self.assertAlmostEqual(np.sum(np.abs(psi) ** 2), 1.0)
        for s in range(2 ** n):
            if bin(s).count("1") != k:
                self.assertAlmostEqual(abs(psi[s]), 0.0, places=12)

    def test_xy_mixer_does_move_amplitude(self):
        psi = apply_xy(np.eye(16)[0b0001].astype(complex), 0, 1, 0.3)
        self.assertGreater(abs(psi[0b10]), 1e-3)

    def test_qaoa_feasible_and_beats_random_average(self):
        r = run_qaoa(self.p, depth=2, seed=7)
        n = self.p.n
        feas = [s for s in range(2 ** n) if bin(s).count("1") == self.p.k]
        self.assertAlmostEqual(sum(r["probabilities"][s] for s in feas), 1.0)
        self.assertLess(r["expectation"], float(np.mean(r["cost"][feas])))
        self.assertGreaterEqual(r["expectation"], min(r["cost"][feas]) - 1e-9)

    def test_qaoa_reproducible(self):
        a = run_qaoa(self.p, depth=1, seed=3, restarts=2, maxiter=40)
        b = run_qaoa(self.p, depth=1, seed=3, restarts=2, maxiter=40)
        self.assertAlmostEqual(a["expectation"], b["expectation"])

    def test_heavy_hex_structure(self):
        n, edges = heavy_hex_edges(3, 9)
        deg = np.zeros(n, int)
        for a, b in edges:
            deg[a] += 1; deg[b] += 1
        self.assertLessEqual(deg.max(), 3)
        seen, stack = {0}, [0]
        while stack:
            u = stack.pop()
            for a, b in edges:
                for v, w in ((a, b), (b, a)):
                    if v == u and w not in seen:
                        seen.add(w); stack.append(w)
        self.assertEqual(len(seen), n)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            Problem(["a", "b"], [0.1, 0.2], [[1, 0], [0, 1]], k=2)
        with self.assertRaises(ValueError):
            Problem(["a", "b", "c"], [0.1, 0.2, 0.3], [[1, 5, 0], [0, 1, 0], [0, 0, 1]], k=1)


if __name__ == "__main__":
    unittest.main()
