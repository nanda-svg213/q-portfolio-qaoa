"""Portfolio problem, QUBO, Ising conversion and exact classical baseline."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import numpy as np


@dataclass
class Problem:
    names: list
    mu: np.ndarray        # expected returns
    sigma: np.ndarray     # covariance matrix (PSD)
    k: int                # number of assets to select (cardinality)
    q: float = 1.0        # risk aversion
    penalty: float = 0.0  # budget penalty A, only used by the penalty-QUBO

    def __post_init__(self):
        self.mu = np.asarray(self.mu, float)
        self.sigma = np.asarray(self.sigma, float)
        n = len(self.names)
        if n < 2 or n > 12:
            raise ValueError("Supported universe size is 2-12 assets.")
        if self.mu.shape != (n,) or self.sigma.shape != (n, n):
            raise ValueError("Shape mismatch between names, returns and covariance.")
        if not np.allclose(self.sigma, self.sigma.T):
            raise ValueError("Covariance matrix must be symmetric.")
        if np.linalg.eigvalsh(self.sigma).min() < -1e-9:
            raise ValueError("Covariance matrix must be positive semidefinite.")
        if not 1 <= self.k <= n - 1:
            raise ValueError("Cardinality k must satisfy 1 <= k <= n-1.")

    @property
    def n(self):
        return len(self.names)


def default_problem(k=3) -> Problem:
    names = ["AAPL", "MSFT", "JNJ", "XOM", "JPM", "NEE"]
    mu = [0.12, 0.10, 0.06, 0.08, 0.09, 0.05]
    vol = np.array([0.22, 0.20, 0.12, 0.18, 0.21, 0.14])
    corr = np.array([
        [1.0, 0.7, 0.2, 0.3, 0.5, 0.1],
        [0.7, 1.0, 0.2, 0.2, 0.5, 0.1],
        [0.2, 0.2, 1.0, 0.1, 0.2, 0.3],
        [0.3, 0.2, 0.1, 1.0, 0.4, 0.2],
        [0.5, 0.5, 0.2, 0.4, 1.0, 0.1],
        [0.1, 0.1, 0.3, 0.2, 0.1, 1.0]])
    return Problem(names, mu, corr * np.outer(vol, vol), k, q=3.0)


def bits(index: int, n: int) -> np.ndarray:
    """Bit i of the basis index is asset i (qubit i, little-endian like Qiskit)."""
    return np.array([(index >> i) & 1 for i in range(n)])


def objective(p: Problem, x) -> float:
    """f(x) = -mu.x + q x^T Sigma x   (minimised; constraint handled separately)."""
    x = np.asarray(x, float)
    return float(-p.mu @ x + p.q * x @ p.sigma @ x)


def is_feasible(p: Problem, x) -> bool:
    return int(np.sum(x)) == p.k


def qubo(p: Problem, with_penalty=True):
    """Return (Q, offset) with f(x)=x^T Q x + offset, x binary (x_i^2 = x_i).
    Penalty term A (sum x - k)^2 is added when with_penalty and p.penalty > 0."""
    Q = p.q * p.sigma.copy()
    Q[np.diag_indices(p.n)] -= p.mu
    off = 0.0
    if with_penalty and p.penalty > 0:
        A, n = p.penalty, p.n
        Q += A * (np.ones((n, n)) - np.eye(n))   # 2A x_i x_j split symmetrically
        Q[np.diag_indices(n)] += A * (1 - 2 * p.k)
        off = A * p.k ** 2
    return Q, off


def qubo_value(Q, off, x):
    x = np.asarray(x, float)
    return float(x @ Q @ x + off)


def ising(Q, off=0.0):
    """x_i=(1-z_i)/2 -> E(z)=sum h_i z_i + sum_{i<j} J_ij z_i z_j + c."""
    n = Q.shape[0]
    Qs = (Q + Q.T) / 2
    J = np.zeros((n, n))
    h = np.zeros(n)
    c = off
    for i in range(n):
        c += Qs[i, i] / 2
        h[i] -= Qs[i, i] / 2
        for j in range(i + 1, n):
            w = 2 * Qs[i, j]
            J[i, j] = w / 4
            h[i] -= w / 4
            h[j] -= w / 4
            c += w / 4
    return h, J, c


def ising_value(h, J, c, x):
    z = 1 - 2 * np.asarray(x, float)
    n = len(z)
    return float(h @ z + sum(J[i, j] * z[i] * z[j] for i in range(n) for j in range(i + 1, n)) + c)


def energies(Q, off, n):
    """Diagonal cost vector over all 2^n basis states."""
    return np.array([qubo_value(Q, off, bits(s, n)) for s in range(2 ** n)])


def brute_force(p: Problem):
    """Exact optimum over all feasible (weight-k) portfolios."""
    best = None
    for combo in combinations(range(p.n), p.k):
        x = np.zeros(p.n)
        x[list(combo)] = 1
        f = objective(p, x)
        if best is None or f < best[0] - 1e-12:
            best = (f, x)
    return {"objective": best[0], "x": best[1].astype(int).tolist(),
            "assets": [p.names[i] for i in np.flatnonzero(best[1])]}
