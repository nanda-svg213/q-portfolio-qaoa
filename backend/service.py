"""Application logic, independent of FastAPI so it can be tested without the web stack."""
from __future__ import annotations
import json, time
from functools import lru_cache
import numpy as np
from quantum.portfolio import Problem, default_problem, objective, brute_force, bits, qubo, ising
from quantum.qaoa_sim import run_qaoa, mixer_layers

MAX_ASSETS, MAX_DEPTH, MAX_SHOTS = 10, 4, 100_000


class InputError(ValueError):
    pass


def default_payload():
    p = default_problem(3)
    vol = np.sqrt(np.diag(p.sigma))
    return {"names": p.names, "returns": p.mu.tolist(), "volatility": vol.tolist(),
            "correlation": (p.sigma / np.outer(vol, vol)).round(6).tolist(),
            "k": p.k, "risk_aversion": p.q, "depth": 3, "shots": 4096, "seed": 7}


def problem_from_payload(d: dict) -> Problem:
    try:
        names = list(d["names"])
        n = len(names)
        if n == 0:
            raise InputError("The asset list is empty.")
        if n > MAX_ASSETS:
            raise InputError(f"At most {MAX_ASSETS} assets are supported (state-vector simulation).")
        if len(set(names)) != n:
            raise InputError("Asset names must be unique.")
        mu = np.array(d["returns"], float)
        vol = np.array(d["volatility"], float)
        corr = np.array(d["correlation"], float)
    except (KeyError, TypeError, ValueError) as e:
        raise InputError(f"Malformed problem definition: {e}")
    if mu.shape != (n,) or vol.shape != (n,) or corr.shape != (n, n):
        raise InputError("Returns, volatilities and correlation matrix must match the number of assets.")
    if not np.all(np.isfinite(mu)) or not np.all(np.isfinite(vol)) or not np.all(np.isfinite(corr)):
        raise InputError("All numeric inputs must be finite numbers.")
    if np.any(vol <= 0):
        raise InputError("Volatility must be positive for every asset.")
    if np.any(np.abs(corr) > 1 + 1e-9) or not np.allclose(corr, corr.T) or not np.allclose(np.diag(corr), 1):
        raise InputError("Correlation must be symmetric, within [-1, 1], with ones on the diagonal.")
    k = int(d.get("k", 0))
    if not 1 <= k <= n - 1:
        raise InputError(f"The number of selected assets must be between 1 and {n - 1} for {n} assets.")
    q = float(d.get("risk_aversion", 1.0))
    if q < 0:
        raise InputError("Risk aversion must be non-negative.")
    try:
        return Problem(names, mu, corr * np.outer(vol, vol), k, q=q)
    except ValueError as e:
        raise InputError(str(e))


def _settings(d):
    depth, shots, seed = int(d.get("depth", 2)), int(d.get("shots", 4096)), int(d.get("seed", 7))
    if not 1 <= depth <= MAX_DEPTH:
        raise InputError(f"QAOA depth must be between 1 and {MAX_DEPTH}.")
    if not 1 <= shots <= MAX_SHOTS:
        raise InputError(f"Shots must be between 1 and {MAX_SHOTS}.")
    return depth, shots, seed


def _metrics(p: Problem, x):
    x = np.asarray(x)
    k = max(int(x.sum()), 1)
    return {"assets": [p.names[i] for i in np.flatnonzero(x)], "x": x.astype(int).tolist(),
            "objective": objective(p, x), "feasible": int(x.sum()) == p.k,
            "constraint_violation": abs(int(x.sum()) - p.k),
            "expected_return": float(p.mu @ x / k),
            "risk": float(np.sqrt(x @ p.sigma @ x) / k)}   # equal-weighted selected assets


def _bitstring(s, n):
    return format(s, f"0{n}b")   # qubit 0 is the right-most character (Qiskit order)


@lru_cache(maxsize=32)
def _optimize_cached(key: str):
    d = json.loads(key)
    p = problem_from_payload(d)
    depth, shots, seed = _settings(d)
    n = p.n
    t0 = time.perf_counter()
    bf = brute_force(p)
    t_classical = time.perf_counter() - t0
    t0 = time.perf_counter()
    r = run_qaoa(p, depth=depth, seed=seed)
    t_qaoa = time.perf_counter() - t0
    probs = r["probabilities"]
    feas = [s for s in range(2 ** n) if bin(s).count("1") == p.k]
    counts, backend_label, aer_error = None, "Local exact statevector simulation (NumPy); shots sampled from it", None
    try:   # execute the Qiskit circuit on Aer when available; angles come from the exact-statevector optimiser
        from qiskit import transpile
        from qiskit_aer import AerSimulator
        from quantum.circuit import build_circuit
        qc = build_circuit(p, r["gammas"], r["betas"])
        qc.measure_all()
        sim = AerSimulator(seed_simulator=seed)
        raw = sim.run(transpile(qc, sim, seed_transpiler=seed), shots=shots).result().get_counts()
        counts = np.zeros(2 ** n, int)
        for key, v in raw.items():
            counts[int(key.replace(" ", ""), 2)] = v
        backend_label = "Qiskit Aer shot execution of the QAOA circuit; angles optimised on an exact NumPy statevector"
    except ImportError:
        pass
    except Exception as e:   # reported to the user, never hidden
        aer_error = f"Aer execution failed ({type(e).__name__}); fell back to NumPy sampling."
    if counts is None:
        counts = np.random.default_rng(seed).multinomial(shots, probs / probs.sum())
    sampled = [s for s in np.flatnonzero(counts)]
    best_s = min(sampled, key=lambda s: objective(p, bits(s, n)))
    top_s = int(np.argmax(probs))
    states = sorted(range(2 ** n), key=lambda s: -probs[s])[:24]
    opt_x = np.array(bf["x"])
    opt_idx = int(sum(int(b) << i for i, b in enumerate(opt_x)))
    q_best = _metrics(p, bits(best_s, n))
    gap = q_best["objective"] - bf["objective"]
    return {
        "reproducibility": {"seed": seed, "depth": depth, "shots": shots, "qubits": n,
                            "backend": backend_label, "aer_error": aer_error},
        "classical": {**_metrics(p, opt_x), "method": "Exhaustive enumeration of feasible portfolios",
                      "runtime_s": t_classical, "feasible_portfolios": len(feas)},
        "qaoa": {**q_best, "bitstring": _bitstring(best_s, n), "runtime_s": t_qaoa,
                 "selection_rule": "lowest-objective bitstring among sampled shots",
                 "most_likely": {**_metrics(p, bits(top_s, n)), "bitstring": _bitstring(top_s, n),
                                 "probability": float(probs[top_s])},
                 "expectation": r["expectation"], "gammas": r["gammas"].tolist(), "betas": r["betas"].tolist(),
                 "probability_feasible": float(sum(probs[s] for s in feas)),
                 "probability_of_optimum": float(probs[opt_idx]),
                 "history": r["history"]},
        "comparison": {"objective_gap": gap, "found_exact_optimum": bool(abs(gap) < 1e-12),
                       "gap_relative_to_feasible_range": gap / (max(r["cost"][feas]) - min(r["cost"][feas]) or 1.0),
                       "mean_feasible_objective": float(np.mean(r["cost"][feas])),
                       "rank_of_qaoa_result": 1 + sum(1 for s in feas if r["cost"][s] < q_best["objective"] - 1e-12)},
        "distribution": [{"bitstring": _bitstring(s, n), "probability": float(probs[s]),
                          "shots": int(counts[s]), "feasible": bin(s).count("1") == p.k,
                          "objective": float(r["cost"][s]), "is_optimum": s == opt_idx,
                          "assets": [p.names[i] for i in range(n) if (s >> i) & 1]} for s in states],
        "feasible_states": [{"assets": [p.names[i] for i in range(n) if (s >> i) & 1], "probability": float(probs[s]),
                             "shots": int(counts[s]), "objective": float(r["cost"][s])}
                            for s in sorted(feas, key=lambda t: r["cost"][t])],
        "problem": {"names": p.names, "k": p.k, "risk_aversion": p.q},
    }


def optimize(d: dict):
    problem_from_payload(d); _settings(d)
    key = json.dumps({k: d[k] for k in ("names", "returns", "volatility", "correlation", "k", "risk_aversion",
                                         "depth", "shots", "seed") if k in d}, sort_keys=True)
    return _optimize_cached(key)


def _qiskit_circuit(d):
    try:
        from quantum.circuit import build_circuit
    except ImportError as e:
        raise RuntimeError("Qiskit is not installed in the backend environment.") from e
    p = problem_from_payload(d)
    res = optimize(d)
    return p, build_circuit(p, res["qaoa"]["gammas"], res["qaoa"]["betas"]), res


def circuit_info(d: dict):
    p, qc, res = _qiskit_circuit(d)
    Q, off = qubo(p, False)
    h, J, c = ising(Q, off)
    ops = {k: int(v) for k, v in qc.count_ops().items()}
    return {"num_qubits": qc.num_qubits, "depth": int(qc.depth()), "gate_counts": ops,
            "diagram": qc.draw("text", fold=-1).single_string(),
            "parameters": {"gammas": res["qaoa"]["gammas"], "betas": res["qaoa"]["betas"]},
            "hamiltonian": {"h": h.tolist(), "J": [[i, j, float(J[i, j])] for i in range(p.n)
                                                    for j in range(i + 1, p.n) if abs(J[i, j]) > 1e-12],
                            "offset": float(c)},
            "mixer": {"type": "XY (ring, even/odd layers)", "equation": "H_XY = sum over ring edges (X_i X_j + Y_i Y_j)",
                      "pairs": [list(pr) for layer in mixer_layers(p.n) for pr in layer],
                      "preserves": f"Hamming weight = {p.k} (number of selected assets)",
                      "initial_state": f"Dicke state |D({p.n},{p.k})>"}}


def transpile_info(d: dict):
    p, qc, _ = _qiskit_circuit(d)
    from quantum.heavy_hex import route_with_qiskit
    if qc.num_qubits > 19:
        raise InputError("Selected problem exceeds the distance-3 heavy-hex device (19 qubits).")
    routed, m = route_with_qiskit(qc, distance=3)
    m["asset_for_logical"] = p.names
    m["routed_gate_counts"] = {k: int(v) for k, v in routed.count_ops().items()}
    return m
