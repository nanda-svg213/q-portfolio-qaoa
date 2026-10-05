# Q-PORTFOLIO
Constraint-aware portfolio optimization with QAOA (Hackathon Track 2: combinatorial optimization, XY mixer, heavy-hex routing).

## Problem Statement
Choose exactly k of n assets to minimise `f(x) = -mu^T x + q x^T Sigma x`, x in {0,1}^n, subject to `sum(x) = k`.

## Why This Problem Matters
Cardinality-constrained portfolio selection is NP-hard in general and is a standard testbed for constrained QAOA.

## Quantum Approach
1. Portfolio -> binary variables -> QUBO -> Ising Hamiltonian.
2. QAOA with a Dicke initial state and an XY mixer, so every measured bitstring has Hamming weight k.
3. Circuit built in Qiskit and routed onto a heavy-hex coupling map with the Qiskit transpiler.
4. Exact classical enumeration as the baseline.

## Mathematical Formulation
### QUBO
Since x_i^2 = x_i: `f(x) = x^T Q x`, `Q = q*Sigma - diag(mu)`. Optional penalty `A (sum x - k)^2` is supported in `quantum/portfolio.py::qubo` but unused by default (the mixer enforces the constraint).
### Ising Formulation
With `x_i = (1 - z_i)/2`: `H_C = sum h_i Z_i + sum_{i<j} J_ij Z_i Z_j + c`. Tested equal to the QUBO on all 2^n bitstrings.
### QAOA
`|psi(gamma,beta)> = prod_l [ U_M(beta_l) U_C(gamma_l) ] |D(n,k)>`. Parameters are optimised classically with COBYLA. Strategy (deterministic given the seed): cost normalised by the feasible-energy range so gamma = O(1); a 7x7 (gamma,beta) grid at p=1 seeds the first start; 6 seeded random restarts; best expectation wins.
### XY Mixer
`H_XY = sum_(i,j) in ring (X_i X_j + Y_i Y_j)`, applied as even then odd ring pairs, each `RXX(2b) RYY(2b)`. It commutes with `sum Z_i`, so weight k is preserved; with a weight-k start every measured state is feasible. Tested: amplitude outside weight k is zero to 1e-12.
### Heavy-Hex Routing
The circuit is transpiled with `CouplingMap.from_heavy_hex(3)` (19 qubits), optimization level 1, seed 11, basis rz/sx/x/cx/swap. SWAPs stay explicit so they are counted directly. Depth, 2-qubit counts and the layout are read from the transpiled circuits.
### Classical Baseline
Enumeration of all C(n,k) feasible portfolios (exact).

## Architecture
`quantum/` (portfolio math, NumPy statevector QAOA, Qiskit circuit, heavy-hex) -> `backend/` (service layer + FastAPI) -> `frontend/` (React/Vite/TS). See `docs/architecture.md`.

## Installation
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install
```
## Running Locally
```
uvicorn backend.app:app --port 8000        # terminal 1
cd frontend && npm run dev                 # terminal 2 -> http://localhost:5173
```
## API
`GET /api/health`, `GET /api/default-problem`, `POST /api/validate`, `POST /api/optimize`, `POST /api/circuit`, `POST /api/transpile`. Errors return `{"error": "..."}` (400 input, 503 Qiskit missing, 500 unexpected) or FastAPI 422 for malformed JSON.
## Testing
`python -m unittest discover tests` (or `pytest`). Tests needing Qiskit/FastAPI skip automatically if absent.
## Demo Instructions
See `docs/demo-script.md`.
## Limitations
- The optimisation loop runs on an exact NumPy statevector simulator; shots are sampled from it. The QAOA angles are optimised on the exact NumPy statevector; when Qiskit Aer is installed the Qiskit circuit is then executed on Aer for the shots (the Results header states which path ran). Qiskit also does circuit construction and routing. No noise model, no IBM hardware.
- Per-asset min/max allocation is not modelled: portfolios are binary selections, reported with equal weights.
- At most 10 assets / p <= 4 / 19 physical qubits.
- QAOA is not guaranteed to find the optimum; the UI reports the gap, rank and P(optimum). Enumeration is faster at these sizes.
## Future Work
Continuous weights on selected assets, noisy simulation with Aer, IBM backend execution, larger heavy-hex devices.
