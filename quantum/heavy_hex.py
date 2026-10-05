"""Heavy-hex coupling graph (degree <= 3) and a Qiskit routing wrapper."""
import numpy as np


def heavy_hex_edges(rows=3, row_len=9):
    """Rows of linear chains joined by bridge qubits at every 4th column,
    alternating offsets between row gaps (the IBM heavy-hex pattern)."""
    edges, nid = [], rows * row_len
    for r in range(rows):
        for c in range(row_len - 1):
            edges.append((r * row_len + c, r * row_len + c + 1))
    for r in range(rows - 1):
        for c in range(0 if r % 2 == 0 else 2, row_len, 4):
            edges += [(r * row_len + c, nid), (nid, (r + 1) * row_len + c)]
            nid += 1
    return nid, edges


def layout_positions(n, edges, seed=1, iters=300):
    """Seeded Fruchterman-Reingold layout so the topology can be drawn; coordinates in [0,1]."""
    rng = np.random.default_rng(seed)
    pos = rng.random((n, 2))
    A = np.zeros((n, n))
    for a, b in edges:
        A[a, b] = A[b, a] = 1
    k = 1 / np.sqrt(n)
    for t in range(iters):
        d = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(d, axis=2) + 1e-9
        rep = (k * k / dist ** 2)[:, :, None] * d
        att = -(A * dist / k)[:, :, None] * d / dist[:, :, None]
        step = (rep + att).sum(axis=1)
        L = np.linalg.norm(step, axis=1, keepdims=True) + 1e-9
        pos += step / L * np.minimum(L, 0.1 * (1 - t / iters))
    pos -= pos.min(0)
    return (pos / (pos.max(0) + 1e-9)).tolist()


def route_with_qiskit(circuit, distance=3, seed=11):
    """Transpile onto Qiskit's heavy-hex coupling map. Every metric is read from the real circuits.
    SWAPs are kept as explicit gates (basis includes 'swap') so inserted SWAPs are counted directly."""
    from qiskit import transpile
    from qiskit.transpiler import CouplingMap
    cmap = CouplingMap.from_heavy_hex(distance)
    basis = ["rz", "sx", "x", "cx", "swap"]
    logical = transpile(circuit, basis_gates=basis, optimization_level=1, seed_transpiler=seed)
    routed = transpile(circuit, coupling_map=cmap, basis_gates=basis,
                       optimization_level=1, seed_transpiler=seed)
    ops_l, ops_r = logical.count_ops(), routed.count_ops()
    two_l = ops_l.get("cx", 0) + ops_l.get("swap", 0)
    two_r = ops_r.get("cx", 0) + ops_r.get("swap", 0)
    edges = sorted({tuple(sorted(e)) for e in cmap.get_edges()})
    layout = routed.layout.final_index_layout() if routed.layout else list(range(circuit.num_qubits))
    return routed, {
        "logical_qubits": circuit.num_qubits, "physical_qubits": cmap.size(),
        "two_qubit_before": int(two_l), "two_qubit_after": int(two_r),
        "cx_before": int(ops_l.get("cx", 0)), "cx_after": int(ops_r.get("cx", 0)),
        "swaps_inserted": int(ops_r.get("swap", 0)),
        "depth_before": int(logical.depth()), "depth_after": int(routed.depth()),
        "mapping": [{"logical": i, "physical": int(q)} for i, q in enumerate(layout)],
        "edges": [list(map(int, e)) for e in edges],
        "positions": layout_positions(cmap.size(), edges),
        "distance": distance}
