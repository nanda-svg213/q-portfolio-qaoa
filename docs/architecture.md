# Architecture
- `quantum/portfolio.py`: Problem, objective, QUBO, Ising, brute force.
- `quantum/qaoa_sim.py`: Dicke state, XY pair rotations, QAOA statevector, optimiser strategy.
- `quantum/circuit.py`: Qiskit circuit mirroring the NumPy gates (StatePreparation, RZ, RZZ, RXX, RYY).
- `quantum/heavy_hex.py`: own heavy-hex generator (tested), Qiskit routing wrapper, layout for drawing.
- `backend/service.py`: validation, orchestration, caching (lru_cache keyed on the request). `backend/app.py`: FastAPI routes and error handlers.
- `frontend/`: React views Optimize, Quantum (circuit, heavy-hex mapping, method notes), Results. Charts are hand-written SVG fed only by API responses.
Flow: UI -> /api/optimize -> service -> run_qaoa + brute_force. Circuit and Hardware tabs re-request with the same payload; results are cached, so parameters match.
