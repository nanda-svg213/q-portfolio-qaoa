import type { ReactElement } from "react";
export function Dots({ vals, peak }: { vals: number[]; peak: number }) {
  const W = 250, H = 84, cw = W / vals.length, mx = Math.max(...vals, 1e-12);
  const out: ReactElement[] = [];
  vals.forEach((v, i) => {
    const n = Math.max(1, Math.round((v / mx) * 8));
    for (let k = 0; k < n; k++)
      out.push(<circle key={`${i}-${k}`} cx={i * cw + cw / 2} cy={H - 5 - k * 9.6} r={Math.min(4.2, cw / 2 - 0.8)} className={i === peak ? "dot pk" : "dot"} />);
  });
  return <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: 250 }} role="img" aria-label="Dot histogram">{out}</svg>;
}

export function Retention({ hist, uid }: { hist: number[]; uid: string }) {
  const step = Math.max(1, Math.floor(hist.length / 40));
  const v: number[] = [];
  for (let i = 0; i < hist.length; i += step) v.push(hist[i]);
  const lo = Math.min(...v), hi = Math.max(...v), sp = hi - lo || 1, W = 270, H = 190, bw = W / v.length;
  const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1].map(t => Math.round(t * (hist.length - 1)));
  return (
    <svg viewBox={`0 0 ${W} ${H + 20}`} width="100%" role="img" aria-label="Optimizer convergence">
      <defs>
        <pattern id={`pin${uid}`} width="2.4" height="4" patternUnits="userSpaceOnUse"><rect width="1.1" height="4" fill="#f472b6" /></pattern>
        <linearGradient id={`fg${uid}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff" /><stop offset="1" stopColor="#000" /></linearGradient>
        <mask id={`mk${uid}`}><rect width={W} height={H} fill={`url(#fg${uid})`} /></mask>
      </defs>
      <g mask={`url(#mk${uid})`} fill={`url(#pin${uid})`}>
        {v.map((x, i) => { const h = 22 + ((x - lo) / sp) * (H - 30); return <rect key={i} x={i * bw} y={H - h} width={bw - 1.6} height={h} />; })}
      </g>
      {ticks.map((e, i) => <text key={i} x={(i * (W - 24)) / 5 + 10} y={H + 14} fill="currentColor" fontSize="9" opacity=".6">{e}</text>)}
    </svg>);
}

export interface TopBar { p: number; assets: string[]; opt: boolean }
export function Bars3d({ top, uid }: { top: TopBar[]; uid: string }) {
  const W = 540, H = 250, L = 44, base = 190, ytop = 14, bw = 78, gap = 40, mx = Math.max(...top.map(t => t.p), 1e-9) * 1.1;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Measurement probability of the five most likely bitstrings">
      <defs>
        <linearGradient id={`gb${uid}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--g1)" /><stop offset="1" stopColor="var(--g2)" /></linearGradient>
        <linearGradient id={`gs${uid}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--g1)" stopOpacity=".55" /><stop offset="1" stopColor="var(--g2)" stopOpacity=".35" /></linearGradient>
        <pattern id={`ht${uid}`} width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4.5" height="9" fill="#1d3d0e" opacity=".55" /></pattern>
      </defs>
      {[0, 0.25, 0.5, 0.75, 1].map(g => { const y = base - g * (base - ytop); return <text key={g} x={L - 8} y={y + 3} textAnchor="end" fontSize="9" fill="currentColor" opacity=".55">{(g * mx * 100).toFixed(1)}%</text>; })}
      {top.map((t, i) => {
        const x = L + 14 + i * (bw + gap), h = (t.p / mx) * (base - ytop), y = base - h;
        return (<g key={i}>
          <line x1={x - gap / 2} x2={x - gap / 2} y1={ytop} y2={base} stroke="currentColor" opacity=".18" />
          <rect x={x} y={y} width={bw} height={h} fill={`url(#gb${uid})`} />
          {t.opt && <rect x={x} y={y} width={bw} height={h} fill={`url(#ht${uid})`} />}
          <polygon points={`${x + bw},${y} ${x + bw + 16},${y + 12} ${x + bw + 16},${base} ${x + bw},${base}`} fill={`url(#gs${uid})`} />
          <rect x={x + bw / 2 - 13} y={y - 9} width="26" height="5" rx="2.5" fill="currentColor" opacity=".35"><title>{(t.p * 100).toFixed(2)}%</title></rect>
          <text x={x + bw / 2} y={base + 16} textAnchor="middle" fontSize="9" fill="currentColor" opacity=".75">{t.assets.join("·")}</text>
          <text x={x + bw / 2} y={base + 29} textAnchor="middle" fontSize="9" fill="currentColor" opacity=".5">{t.opt ? "exact optimum" : ""}</text>
        </g>);
      })}
    </svg>);
}

export function Blob({ uid }: { uid: string }) {
  return (
    <svg className="blob" viewBox="0 0 360 330" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs><linearGradient id={`bg${uid}`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#2f7a4a" /><stop offset="1" stopColor="#0d2e1e" /></linearGradient></defs>
      <path d="M-20 40C60 0 120 90 90 170S-10 260 -20 330Z" fill={`url(#bg${uid})`} opacity=".85" />
      <path d="M380 -20C300 60 330 140 250 200S120 260 200 360L380 360Z" fill={`url(#bg${uid})`} opacity=".7" />
      <path d="M130 360C150 290 250 300 300 250S340 340 340 360Z" fill="#1a4d33" opacity=".6" />
    </svg>);
}

export function Topology({ edges, positions, used }: { edges: number[][]; positions: number[][]; used: Map<number, number> }) {
  const S = 380, P = 16, px = (v: number[]) => [P + v[0] * (S - 2 * P), P + v[1] * (S - 2 * P)];
  return (
    <svg viewBox={`0 0 ${S} ${S}`} width="100%" style={{ maxWidth: 440 }} role="img" aria-label="Heavy-hex coupling graph">
      {edges.map(([a, b]) => { const A = px(positions[a]), B = px(positions[b]); const on = used.has(a) && used.has(b);
        return <line key={`${a}-${b}`} x1={A[0]} y1={A[1]} x2={B[0]} y2={B[1]} stroke={on ? "var(--dotpk)" : "currentColor"} strokeWidth={on ? 2 : 1} opacity={on ? 1 : 0.3} />; })}
      {positions.map((p, i) => { const [cx, cy] = px(p), on = used.has(i);
        return (<g key={i}><circle cx={cx} cy={cy} r={on ? 9 : 6} className={on ? "dot pk" : "dot"} />
          {on && <text x={cx} y={cy + 3} textAnchor="middle" fontSize="7" fill="#06210f">q{used.get(i)}</text>}</g>); })}
    </svg>);
}
