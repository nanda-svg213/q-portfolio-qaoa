# FINAL STATUS

**This project is NOT fully verified.** The build sandbox blocks package registries by network policy
(`pip` -> "No matching distribution found for qiskit"; `npm install` -> HTTP 403), so Qiskit, Qiskit Aer, FastAPI, React and Vite
were never installed or run. Statements below are limited to what was actually executed.

## Implemented
- Portfolio objective, QUBO (+optional penalty), Ising, exact brute-force baseline (`quantum/portfolio.py`).
- XY ring mixer + Dicke start, NumPy exact-statevector QAOA, deterministic optimiser (normalised cost, p=1 grid warm start, seeded restarts) (`quantum/qaoa_sim.py`).
- Qiskit circuit builder and heavy-hex routing wrapper (`quantum/circuit.py`, `quantum/heavy_hex.py`); optional Aer shot execution in `/api/optimize` (angles are optimised on the NumPy statevector; the Results header states which path ran).
- FastAPI: `/api/health, default-problem, validate, optimize, circuit, transpile`.
- React/Vite/TS UI (Optimize, Quantum, Results) in the supplied reference style, editable built-in portfolio dataset. Full-viewport layout (no outer gray frame) over a light CSS-embedded SVG wave background.

## Tests executed: 17 run, 13 passed, 4 skipped, 0 failed (`python -m unittest discover -s tests -t .`)
Objective, QUBO, penalty, Ising vs QUBO on all bitstrings, brute force, XY weight preservation, QAOA feasibility/reproducibility, own heavy-hex graph structure, service-layer optimise/validation.
Also executed: Python compile check; TypeScript pass whose only errors are the missing React type packages; Chromium rendering of a static page using the real `styles.css` (earlier build) at 1440/768/390/320 px showing no horizontal overflow and the stage filling the viewport. That was a CSS/layout check, not a run of the React app.

## Tests skipped (4) and why
- Qiskit vs NumPy statevector (incl. XY mixer on a real circuit), heavy-hex transpile metrics, `/api/circuit` + `/api/transpile` logic: qiskit not installable here.
- FastAPI TestClient endpoint test: fastapi not installable here.

## Not run
Qiskit/Aer execution; uvicorn start; `npm install`, `npm run build`; the React app in a browser; end-to-end UI -> API -> QAOA -> results; clean-setup run. The Dicke-state `StatePreparation` circuit is unchecked.

## Remaining verification (on a machine with network access)
```
pip install -r requirements.txt && python -m unittest discover -s tests -t .     # expect 0 skipped
cd frontend && npm install && npm run build
uvicorn backend.app:app --host 127.0.0.1 --port 8000 & (cd frontend && npm run dev)
```
Then click through Optimize -> Run -> Results -> Quantum.

## Known limitations
- Optimiser runs on NumPy, not Aer; shots come from Aer only when installed.
- Reference result (default problem, seed 7): optimum JNJ+XOM+NEE; QAOA's most likely portfolio is the optimum only at p=3 (P=0.369). Other problems are unmeasured.
- Portfolio data is the built-in dataset or user-typed values; there is no market-data feed.
- No per-asset allocations (equal-weight reporting); <= 10 assets, p <= 4, 19 physical qubits; no noise model, no hardware, no speed-up claim.
