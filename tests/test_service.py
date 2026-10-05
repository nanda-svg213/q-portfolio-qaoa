import unittest, copy
import numpy as np
from backend import service


class Service(unittest.TestCase):
    def test_default_optimize_is_feasible_and_consistent(self):
        d = service.default_payload()
        r = service.optimize(d)
        self.assertTrue(r["qaoa"]["feasible"])
        self.assertEqual(sum(r["qaoa"]["x"]), d["k"])
        self.assertGreaterEqual(r["comparison"]["objective_gap"], -1e-12)
        self.assertAlmostEqual(r["qaoa"]["probability_feasible"], 1.0, places=9)
        self.assertAlmostEqual(sum(s["probability"] for s in r["distribution"]) <= 1 + 1e-9, True)
        self.assertEqual(r, service.optimize(copy.deepcopy(d)))   # deterministic

    def test_validation_errors_are_readable(self):
        d = service.default_payload()
        for mut, msg in [({"k": 6}, "between 1 and"), ({"names": []}, "empty"),
                         ({"volatility": [0] * 6}, "positive"), ({"depth": 9}, "depth"),
                         ({"returns": [0.1]}, "match")]:
            bad = {**d, **mut}
            with self.assertRaises(service.InputError) as c:
                service.optimize(bad)
            self.assertIn(msg, str(c.exception))

    def test_oversized_universe_rejected(self):
        n = service.MAX_ASSETS + 1
        d = {"names": [f"A{i}" for i in range(n)], "returns": [0.1] * n, "volatility": [0.2] * n,
             "correlation": np.eye(n).tolist(), "k": 3}
        with self.assertRaises(service.InputError):
            service.problem_from_payload(d)

    def test_api_endpoints(self):
        try:
            from fastapi.testclient import TestClient
            from backend.app import app
        except ImportError:
            self.skipTest("fastapi not installed")
        c = TestClient(app)
        self.assertEqual(c.get("/api/health").status_code, 200)
        d = c.get("/api/default-problem").json()
        self.assertEqual(c.post("/api/optimize", json=d).status_code, 200)
        self.assertEqual(c.post("/api/optimize", json={**d, "k": 6}).status_code, 400)
        self.assertEqual(c.post("/api/optimize", json={"names": []}).status_code, 422)


class QiskitRuntime(unittest.TestCase):
    def setUp(self):
        try:
            import qiskit  # noqa
        except ImportError:
            self.skipTest("qiskit not installed")

    def test_circuit_and_transpile(self):
        d = service.default_payload() | {"depth": 1}
        c = service.circuit_info(d)
        self.assertEqual(c["num_qubits"], 6)
        m = service.transpile_info(d)
        self.assertEqual(m["logical_qubits"], 6)
        self.assertGreaterEqual(m["two_qubit_after"], 0)
        self.assertEqual(len({x["physical"] for x in m["mapping"]}), 6)
        self.assertTrue(all(len(e) == 2 for e in m["edges"]))
