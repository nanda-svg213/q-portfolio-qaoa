import { useEffect, useState, type ReactNode } from "react";
import { api, Payload } from "./api";
import { Dots, Retention, Bars3d, Blob, Topology } from "./charts";

type Tab = "Optimize" | "Quantum" | "Results";
type Mode = "split" | "dark" | "light";
const TABS: Tab[] = ["Optimize", "Quantum", "Results"];
const f = (v: number, d = 4) => v.toFixed(d);
const pc = (v: number) => (100 * v).toFixed(1) + "%";
const binom = (n: number, k: number) => { if (!(k >= 0 && k <= n)) return 0; let r = 1; for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i; return Math.round(r); };

type Remote = { data?: any; error?: string; loading: boolean };
function useRemote(fn: (() => Promise<any>) | null, dep: unknown): Remote {
  const [s, set] = useState<Remote>({ loading: false });
  useEffect(() => {
    if (!fn) { set({ loading: false }); return; }
    let live = true;
    set({ loading: true });
    fn().then(data => live && set({ data, loading: false })).catch(e => live && set({ error: e.message, loading: false }));
    return () => { live = false; };
  }, [dep]);
  return s;
}
function Async({ s, children }: { s: Remote; children: (d: any) => ReactNode }) {
  if (s.loading) return <p className="mut" role="status">Computing…</p>;
  if (s.error) return <p className="err" role="alert">{s.error}</p>;
  return s.data ? <>{children(s.data)}</> : null;
}
const Info = ({ t }: { t: string }) => <span className="info" tabIndex={0} title={t} aria-label={t}>i</span>;

export default function App() {
  const [tab, setTab] = useState<Tab>("Results");
  const [mode, setMode] = useState<Mode>("light");
  const [p, setP] = useState<Payload | null>(null);
  const [ran, setRan] = useState<Payload | null>(null);
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [qiskit, setQiskit] = useState<string | null | undefined>();

  useEffect(() => {
    api.defaults().then(d => { setP(d); setTab("Optimize"); }).catch(e => { setErr(e.message); setTab("Optimize"); });
    api.health().then(h => setQiskit(h.qiskit)).catch(() => setQiskit(undefined));
  }, []);

  async function run() {
    if (!p) return;
    setBusy(true); setErr(undefined);
    try { const snap = structuredClone(p); setRes(await api.optimize(snap)); setRan(snap); setTab("Results"); }
    catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  }
  const circ = useRemote(tab === "Quantum" && ran ? () => api.circuit(ran) : null, JSON.stringify([tab, ran]));
  const hw = useRemote(tab === "Quantum" && ran ? () => api.transpile(ran) : null, JSON.stringify([tab, ran]));
  const ctx = { tab, setTab, p, setP, ran, res, busy, err, run, circ, hw };
  const cycle = () => setMode(mode === "split" ? "dark" : mode === "dark" ? "light" : "split");

  return (
    <>
      <div className="stage" data-mode={mode}>
        <Layer cls="dark" uid="d" ctx={ctx} cycle={cycle} />
        <Layer cls="light" uid="l" ctx={ctx} cycle={cycle} hidden={mode === "split"} />
      </div>
      <p className="foot">Local quantum simulation · Qiskit {qiskit === undefined ? "backend unreachable" : qiskit ?? "not installed (circuit and routing views unavailable)"}</p>
    </>);
}

function Layer({ cls, uid, ctx, cycle, hidden }: { cls: string; uid: string; ctx: any; cycle: () => void; hidden?: boolean }) {
  const { tab, setTab, p, ran, res } = ctx;
  const title = tab === "Results" ? "Overview" : tab;
  return (
    <div className={`layer ${cls}`} aria-hidden={hidden || undefined}>
      <nav className="nav" aria-label="Sections">
        {TABS.map(t => <button key={t} className={t === tab ? "on" : ""} onClick={() => setTab(t)} aria-current={t === tab ? "page" : undefined}>{t}</button>)}
        <div className="corner">
          <button className="circ" onClick={cycle} aria-label="Cycle theme: split, dark, light">◐</button>
          <span className="circ brand" aria-hidden="true">QP</span>
        </div>
      </nav>
      <div className="head">
        <h1>{title}</h1>
        <div className="pills">
          {ran && tab === "Results" ? <><span className="pill f">{ran.names.length} assets</span><i>compared to</i><span className="pill">exact optimum</span><span className="pill f">k = {ran.k}</span><span className="pill f">p = {ran.depth}</span></>
            : p && <span className="pill f">{p.names.length} assets · k = {p.k}</span>}
        </div>
      </div>
      {tab === "Optimize" && (p ? <OptimizeView ctx={ctx} /> : <>{ctx.err && <p className="err" role="alert">{ctx.err}</p>}<p className="mut">Loading default problem…</p></>)}
      {tab === "Results" && (res && ran ? <ResultsView r={res} names={ran.names} uid={uid} /> : <Empty ctx={ctx} />)}
      {tab === "Quantum" && (ran ? <QuantumView ctx={ctx} /> : <Empty ctx={ctx} />)}
    </div>);
}

function Empty({ ctx }: { ctx: any }) {
  return <div className="card"><h3>No optimization yet</h3><p className="mut">Open <button className="link" onClick={() => ctx.setTab("Optimize")}>Optimize</button> and press Run Optimization.</p></div>;
}

function OptimizeView({ ctx }: { ctx: any }) {
  const { p, setP, run, busy, err } = ctx;
  return (
    <div className="two">
      <div className="card"><h3>Portfolio universe</h3><EditableUniverse p={p} setP={setP} /></div>
      <div className="card"><h3>Problem and QAOA settings</h3><Settings p={p} setP={setP} run={run} busy={busy} err={err} /></div>
    </div>);
}

function EditableUniverse({ p, setP }: { p: Payload; setP: (p: Payload) => void }) {
  const n = p.names.length;
  const upd = (patch: Partial<Payload>) => setP({ ...p, ...patch });
  const num = (v: string) => (v === "" ? NaN : Number(v));
  const val = (x: number) => (Number.isNaN(x) ? "" : x);
  const setArr = (key: "returns" | "volatility", i: number, v: string) => upd({ [key]: p[key].map((x, j) => (j === i ? num(v) : x)) } as Partial<Payload>);
  const setCorr = (i: number, j: number, v: string) => upd({ correlation: p.correlation.map((row, a) => row.map((x, b) => ((a === i && b === j) || (a === j && b === i) ? num(v) : x))) });
  const rename = (i: number, v: string) => upd({ names: p.names.map((x, j) => (j === i ? v : x)) });
  const add = () => upd({ names: [...p.names, `ASSET${n + 1}`], returns: [...p.returns, 0.07], volatility: [...p.volatility, 0.15],
    correlation: [...p.correlation.map(r => [...r, 0.2]), [...Array(n).fill(0.2), 1]] });
  const drop = (i: number) => { const keep = (_: unknown, j: number) => j !== i;
    upd({ names: p.names.filter(keep), returns: p.returns.filter(keep), volatility: p.volatility.filter(keep), correlation: p.correlation.filter(keep).map(r => r.filter(keep)), k: Math.min(p.k, n - 2) }); };
  return (<>
    <div className="scroll"><table><thead><tr><th>Asset</th><th>Expected return</th><th>Volatility</th><th /></tr></thead>
      <tbody>{p.names.map((nm, i) => (<tr key={i}>
        <td><input aria-label={`Name ${i + 1}`} value={nm} onChange={e => rename(i, e.target.value)} /></td>
        <td><input aria-label={`Return ${nm}`} type="number" step="0.01" value={val(p.returns[i])} onChange={e => setArr("returns", i, e.target.value)} /></td>
        <td><input aria-label={`Volatility ${nm}`} type="number" step="0.01" value={val(p.volatility[i])} onChange={e => setArr("volatility", i, e.target.value)} /></td>
        <td><button className="btn" onClick={() => drop(i)} disabled={n <= 3} aria-label={`Remove ${nm}`}>Remove</button></td></tr>))}</tbody></table></div>
    <p><button className="btn" onClick={add} disabled={n >= 10}>Add asset</button></p>
    <details><summary>Correlation matrix</summary>
      <div className="scroll"><table className="corr"><thead><tr><th />{p.names.map((x, i) => <th key={i}>{x}</th>)}</tr></thead>
        <tbody>{p.correlation.map((row, i) => (<tr key={i}><th>{p.names[i]}</th>{row.map((v, j) => (<td key={j}>
          {j > i ? <input aria-label={`Correlation ${p.names[i]} ${p.names[j]}`} type="number" step="0.05" min="-1" max="1" value={val(v)} onChange={e => setCorr(i, j, e.target.value)} /> : <span className="mut">{j === i ? "1" : Number.isNaN(v) ? "" : f(v, 2)}</span>}</td>))}</tr>))}</tbody></table></div>
    </details>
  </>);
}

function Settings({ p, setP, run, busy, err }: { p: Payload; setP: (p: Payload) => void; run: () => void; busy: boolean; err?: string }) {
  const n = p.names.length;
  const upd = (patch: Partial<Payload>) => setP({ ...p, ...patch });
  const num = (v: string) => (v === "" ? NaN : Number(v));
  const val = (x: number) => (Number.isNaN(x) ? "" : x);
  return (<>
    <p className="eq">minimise −μᵀx + q·xᵀΣx subject to Σxᵢ = k, x ∈ {"{0,1}"}ⁿ</p>
    <div className="form">
      <label>Assets to select (k)<input type="number" min={1} max={n - 1} value={val(p.k)} onChange={e => upd({ k: num(e.target.value) })} /></label>
      <label>Risk aversion (q)<input type="number" step="0.5" min={0} value={val(p.risk_aversion)} onChange={e => upd({ risk_aversion: num(e.target.value) })} /></label>
      <label>Depth p<input type="number" min={1} max={4} value={val(p.depth)} onChange={e => upd({ depth: num(e.target.value) })} /></label>
      <label>Shots<input type="number" min={1} step={256} value={val(p.shots)} onChange={e => upd({ shots: num(e.target.value) })} /></label>
      <label>Seed<input type="number" value={val(p.seed)} onChange={e => upd({ seed: num(e.target.value) })} /></label>
      <label>Mixer<input value="XY (ring)" readOnly /></label>
    </div>
    <p className="mut">{n} assets → {n} qubits · {binom(n, p.k)} feasible portfolios of {2 ** n} bitstrings</p>
    {err && <p className="err" role="alert">{err}</p>}
    <button className="primary" onClick={run} disabled={busy}>{busy ? "Running…" : "Run Optimization"}</button>
    <p className="mut">Local quantum simulation. No hardware is used.</p>
  </>);
}

function ResultsView({ r, names, uid }: { r: any; names: string[]; uid: string }) {
  const q = r.qaoa, c = r.classical, m = r.comparison, rp = r.reproducibility;
  const F: any[] = r.feasible_states;
  const peak = F.reduce((a, x, i) => (x.probability > F[a].probability ? i : a), 0);
  const shotPeak = F.reduce((a, x, i) => (x.shots > F[a].shots ? i : a), 0);
  const optIdx = F.reduce((a, x, i) => (x.objective < F[a].objective ? i : a), 0);
  const top = r.distribution.slice(0, 5).map((d: any) => ({ p: d.probability, assets: d.assets, opt: d.is_optimum }));
  return (
    <>
      {rp.aer_error && <p className="warn" role="status">{rp.aer_error}</p>}
      {!m.found_exact_optimum && <p className="warn" role="status">QAOA's best sampled portfolio is not the exact optimum: gap {f(m.objective_gap)}, rank {m.rank_of_qaoa_result} of {c.feasible_portfolios}.</p>}
      <div className="grid">
        <div className="card r1"><h3>Convergence</h3><Info t="Best-restart optimizer trace: objective expectation per evaluation (downsampled to 40 bars)" />
          <p className="mut" style={{ margin: "14px 0 4px" }}>⟨C⟩ {f(q.history[0])} → {f(q.expectation)}</p><Retention hist={q.history} uid={uid} /></div>
        <div className="card"><h3>Feasible portfolios</h3><Info t="Probability of each feasible portfolio, ordered best to worst objective" />
          <span className="tag" style={{ position: "absolute", left: "44%", top: 46 }}>Peak: {F[peak].assets.join(" · ")}</span>
          <div className="stat"><div className="big">{F.length}</div><Dots vals={F.map(x => x.probability)} peak={peak} />
            <div style={{ textAlign: "right" }}><span className="mut">vs uniform {pc(1 / F.length)}</span><div style={{ fontSize: 18 }}>P(opt) {pc(q.probability_of_optimum)}</div></div></div></div>
        <div className="card"><h3>Shots</h3><Info t="Sampled counts per feasible portfolio (same ordering)" />
          <div className="stat"><div className="big">{rp.shots}</div><Dots vals={F.map(x => x.shots)} peak={shotPeak} />
            <div style={{ textAlign: "right" }}><span className="mut">optimum drawn</span><div style={{ fontSize: 18 }}>{F[optIdx].shots}×</div></div></div></div>
        <div className="card r1"><h3>QAOA portfolio</h3><Info t="Best sampled portfolio and its objective; bars are exact fractions from this run" />
          <div className="big" style={{ marginTop: 20 }}>{f(q.objective)}<span className="badge">gap {f(m.objective_gap)}</span></div>
          <div className="rows">
            <div className="row"><div><span>P(optimum)</span><span>{pc(q.probability_of_optimum)}</span></div><div className="track"><div className="fill s1" style={{ width: `${100 * q.probability_of_optimum}%` }} /></div></div>
            <div className="row"><div><span>P(feasible)</span><span>{pc(q.probability_feasible)}</span></div><div className="track"><div className="fill s2" style={{ width: `${100 * q.probability_feasible}%` }} /></div></div>
            <div className="row"><div><span>Assets selected</span><span>{q.assets.length}/{names.length}</span></div><div className="track"><div className="fill s3" style={{ width: `${(100 * q.assets.length) / names.length}%` }} /></div></div>
          </div>
          <p className="mut">{q.assets.join(" · ")} · return {pc(q.expected_return)} · risk {pc(q.risk)}</p>
          <p className="mut">Classical optimum: {c.assets.join(" · ")} ({f(c.objective)}, exact enumeration, {(c.runtime_s * 1000).toFixed(2)} ms)</p></div>
        <div className="card r3" style={{ minHeight: 340 }}><h3>Measurement probabilities</h3><Info t="Five most likely bitstrings. The hatched bar is the exact classical optimum." />
          <div style={{ marginTop: 8, paddingBottom: 70 }}><Bars3d top={top} uid={uid} /></div>
          <div className="cmd"><small>{rp.backend}. Exact enumeration is the baseline; no speed-up is claimed.</small>seed {rp.seed} · {rp.qubits} qubits · mixer XY · depth <b>p={rp.depth}</b> · {rp.shots} shots</div></div>
        <div className="card ins" style={{ minHeight: 340 }}><Blob uid={uid} /><span className="tag">Insights</span>
          <div className="big" style={{ marginTop: 74 }}>{pc(q.most_likely.probability)}</div>
          <p style={{ fontSize: 15, margin: "10px 0" }}>Most likely portfolio at p={rp.depth}: {q.most_likely.assets.join(" · ")}.{m.found_exact_optimum ? " The best sampled portfolio is the exact classical optimum." : " The best sampled portfolio is not the exact optimum."}</p>
          <p className="mut" style={{ color: "inherit", opacity: 0.75 }}>Gap {f(m.objective_gap)}; rank {m.rank_of_qaoa_result} of {c.feasible_portfolios}. Mean feasible objective {f(m.mean_feasible_objective)} vs QAOA ⟨C⟩ {f(q.expectation)}.</p></div>
      </div>
    </>);
}

function QuantumView({ ctx }: { ctx: any }) {
  return (
    <div className="stack">
      <Async s={ctx.circ}>{(c: any) => (<>
        <div className="tstats">
          <div className="ts"><span className="k">Qubits</span><span className="v">{c.num_qubits}</span></div>
          <div className="ts"><span className="k">Depth</span><span className="v">{c.depth}</span></div>
          <div className="ts"><span className="k">Layers p</span><span className="v">{c.parameters.gammas.length}</span></div>
          <div className="ts"><span className="k">Mixer</span><span className="v">XY</span></div>
        </div>
        <div className="two">
          <div className="card"><h3>XY mixer</h3><p className="eq">{c.mixer.equation}</p>
            <p>Preserves: {c.mixer.preserves}. Initial state: {c.mixer.initial_state}.</p>
            <p className="mut">Ring pairs: {c.mixer.pairs.map((x: number[]) => `(${x[0]},${x[1]})`).join(" ")}. Each pair is RXX(2β)·RYY(2β).</p>
            <h3 style={{ marginTop: 16 }}>Gate counts</h3>
            <table><tbody>{Object.entries(c.gate_counts).map(([g, n]) => <tr key={g}><th>{g}</th><td>{String(n)}</td></tr>)}</tbody></table></div>
          <div className="card"><h3>Cost Hamiltonian</h3><p className="eq">H_C = Σ hᵢ Zᵢ + Σ Jᵢⱼ ZᵢZⱼ + {f(c.hamiltonian.offset)}</p>
            <details><summary>Coefficients ({c.hamiltonian.J.length} couplings)</summary>
              <p className="mono">h = [{c.hamiltonian.h.map((x: number) => f(x)).join(", ")}]</p>
              <p className="mono">{c.hamiltonian.J.map((t: number[]) => `J(${t[0]},${t[1]})=${f(t[2])}`).join("  ")}</p></details>
            <p className="mono">γ = [{c.parameters.gammas.map((x: number) => f(x)).join(", ")}]  β = [{c.parameters.betas.map((x: number) => f(x)).join(", ")}]</p></div>
        </div>
        <div className="card"><h3>Circuit</h3><div className="scroll"><pre>{c.diagram}</pre></div></div>
      </>)}</Async>
      <h2 className="sect">Heavy-hex hardware mapping</h2>
      <Async s={ctx.hw}>{(m: any) => {
        const used = new Map<number, number>(m.mapping.map((x: any) => [x.physical, x.logical]));
        return (<>
          <div className="tstats">
            <div className="ts"><span className="k">Logical qubits</span><span className="v">{m.logical_qubits}</span></div>
            <div className="ts"><span className="k">Physical qubits</span><span className="v">{m.physical_qubits}</span></div>
            <div className="ts"><span className="k">SWAPs inserted</span><span className="v">{m.swaps_inserted}</span></div>
            <div className="ts"><span className="k">2-qubit gates</span><span className="v">{m.two_qubit_before} → {m.two_qubit_after}</span></div>
            <div className="ts"><span className="k">Depth</span><span className="v">{m.depth_before} → {m.depth_after}</span></div>
          </div>
          <div className="two">
            <div className="card"><h3>Heavy-hex coupling graph</h3><Topology edges={m.edges} positions={m.positions} used={used} />
              <p className="mut">Highlighted qubits hold a logical qubit (label qN). Heavy-hex distance {m.distance}.</p></div>
            <div className="card"><h3>Logical → physical mapping</h3>
              <table><thead><tr><th>Logical</th><th>Asset</th><th>Physical</th></tr></thead>
                <tbody>{m.mapping.map((x: any) => <tr key={x.logical}><td>q{x.logical}</td><td>{m.asset_for_logical[x.logical]}</td><td>{x.physical}</td></tr>)}</tbody></table>
              <p className="mut">Qiskit transpiler, optimization level 1, seed 11, basis rz/sx/x/cx/swap. All numbers are counted from the transpiled circuits{m.swaps_inserted === 0 ? "; no SWAPs were needed here" : ""}.</p></div>
          </div></>);
      }}</Async>
      <Method />
    </div>);
}

function Method() {
  const items: [string, string][] = [
    ["Portfolio formulation", "Choose exactly k of n assets. With xᵢ = 1 when asset i is held, minimise −μᵀx + q·xᵀΣx. Return and risk assume equal weights over the selected assets."],
    ["QUBO and Ising", "Because xᵢ² = xᵢ the objective is xᵀQx with Q = qΣ − diag(μ). Substituting xᵢ = (1 − Zᵢ)/2 gives H_C = Σ hᵢZᵢ + Σ JᵢⱼZᵢZⱼ + const, checked against the QUBO on all bitstrings in the tests."],
    ["QAOA", "Start in a Dicke state, then per layer apply exp(−iγH_C) and the XY mixer. γ and β are optimised with COBYLA from a p = 1 grid warm start plus seeded restarts, with the cost normalised by the feasible range."],
    ["XY mixer", "Σ (XᵢXⱼ + YᵢYⱼ) over ring edges commutes with the total excitation number, so Hamming weight k never changes and every measured bitstring is feasible."],
    ["Heavy-hex routing", "IBM devices only couple neighbours on a heavy-hex lattice (degree ≤ 3). The Qiskit transpiler maps the circuit and inserts SWAPs; depth, two-qubit gate count and SWAP count above are counted from the circuits."],
    ["Classical baseline", "All C(n,k) feasible portfolios are enumerated, giving the exact optimum. It is faster than the simulated QAOA at this size; the comparison shows solution quality, not speed."],
  ];
  return <div className="card"><h3>Method</h3>{items.map(([t, b]) => <details key={t}><summary>{t}</summary><p>{b}</p></details>)}</div>;
}
