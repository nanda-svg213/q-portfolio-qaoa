export interface Payload {
  names: string[]; returns: number[]; volatility: number[]; correlation: number[][];
  k: number; risk_aversion: number; depth: number; shots: number; seed: number;
}
async function call<T>(path: string, body?: Payload): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined);
  } catch {
    throw new Error("Backend unavailable. Start it with: uvicorn backend.app:app --port 8000");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? "Invalid input: " + data.detail.map((d: any) => `${(d.loc || []).slice(1).join(".")} ${d.msg}`).join("; ") : undefined;
    throw new Error(data.error || detail || `Request failed (${res.status})`);
  }
  return data as T;
}
export const api = {
  health: () => call<{ status: string; qiskit: string | null}>("/api/health"),
  defaults: () => call<Payload>("/api/default-problem"),
  optimize: (p: Payload) => call<any>("/api/optimize", p),
  circuit: (p: Payload) => call<any>("/api/circuit", p),
  transpile: (p: Payload) => call<any>("/api/transpile", p),
};
