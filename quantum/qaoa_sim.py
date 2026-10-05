"""Exact statevector QAOA with an XY (ring) mixer, in plain NumPy.
Used as the reference implementation that the Qiskit circuit is checked against."""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize
from .portfolio import Problem, qubo, energies


def ring_pairs(n):
    return [(i, (i + 1) % n) for i in range(n)] if n > 2 else [(0, 1)]


def mixer_layers(n):
    """Even/odd ring pairs; pairs inside a layer are disjoint so they commute."""
    pairs = ring_pairs(n)
    even = [p for idx, p in enumerate(pairs) if idx % 2 == 0]
    odd = [p for idx, p in enumerate(pairs) if idx % 2 == 1]
    return [l for l in (even, odd) if l]


def initial_state(n, k):
    """Dicke state |D_n^k>: uniform superposition of all weight-k basis states (all feasible)."""
    psi = np.zeros(2 ** n, complex)
    idx = [s for s in range(2 ** n) if bin(s).count("1") == k]
    psi[idx] = 1 / np.sqrt(len(idx))
    return psi


def apply_xy(psi, i, j, beta):
    """exp(-i beta (X_i X_j + Y_i Y_j)): rotates inside span{|01>,|10>}, fixes |00>,|11>."""
    idx = np.arange(len(psi))
    bi, bj = (idx >> i) & 1, (idx >> j) & 1
    a = np.flatnonzero((bi == 1) & (bj == 0))
    b = a ^ (1 << i) ^ (1 << j)
    out = psi.copy()
    c, s = np.cos(2 * beta), -1j * np.sin(2 * beta)
    out[a] = c * psi[a] + s * psi[b]
    out[b] = c * psi[b] + s * psi[a]
    return out


def qaoa_state(cost, n, k, gammas, betas):
    psi = initial_state(n, k)
    for g, b in zip(gammas, betas):
        psi = psi * np.exp(-1j * g * cost)
        for layer in mixer_layers(n):
            for (i, j) in layer:
                psi = apply_xy(psi, i, j, b)
    return psi


def run_qaoa(p: Problem, depth=2, seed=7, restarts=6, maxiter=200, grid=7):
    """Cost is normalised by the feasible-energy span so gamma is O(1). Starts: a (gamma,beta)
    grid at p=1 extended layer by layer (INTERP-style), plus seeded random restarts. COBYLA polish."""
    n = p.n
    Q, off = qubo(p, with_penalty=False)       # XY mixer enforces the budget: no penalty
    cost = energies(Q, off, n)
    feas = np.array([bin(s).count("1") == p.k for s in range(2 ** n)])
    span = float(cost[feas].max() - cost[feas].min()) or 1.0
    norm = (cost - cost[feas].min()) / span
    rng = np.random.default_rng(seed)

    def expval(t):
        psi = qaoa_state(norm, n, p.k, t[:depth], t[depth:])
        return float(np.real(np.sum(np.abs(psi) ** 2 * norm)))

    starts = []
    gs, bs = np.linspace(0.1, 2 * np.pi, grid), np.linspace(0.1, np.pi, grid)
    g1, b1 = min(((g, b) for g in gs for b in bs),
                 key=lambda gb: expval_p(norm, n, p.k, *gb))
    starts.append(np.r_[np.full(depth, g1), np.full(depth, b1)])
    for _ in range(restarts):
        starts.append(np.r_[rng.uniform(0, 2 * np.pi, depth), rng.uniform(0, np.pi, depth)])
    best = None
    for x0 in starts:
        trace = []
        res = minimize(lambda t: (trace.append(expval(t)), trace[-1])[1], x0,
                       method="COBYLA", options={"maxiter": maxiter})
        if best is None or res.fun < best[0].fun:
            best = (res, trace)
    res, history = best
    psi = qaoa_state(norm, n, p.k, res.x[:depth], res.x[depth:])
    return {"gammas": res.x[:depth] / span, "betas": res.x[depth:], "gammas_normalised": res.x[:depth],
            "span": span, "expectation": float(res.fun * span + cost[feas].min()),
            "probabilities": np.abs(psi) ** 2, "cost": cost, "history": [h * span + cost[feas].min() for h in history]}


def expval_p(norm, n, k, g, b):
    psi = qaoa_state(norm, n, k, [g], [b])
    return float(np.real(np.sum(np.abs(psi) ** 2 * norm)))
