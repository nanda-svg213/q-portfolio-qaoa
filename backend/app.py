from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from . import service

app = FastAPI(title="Q-PORTFOLIO API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


class ProblemIn(BaseModel):
    names: list[str] = Field(..., max_length=service.MAX_ASSETS + 5)
    returns: list[float]
    volatility: list[float]
    correlation: list[list[float]]
    k: int
    risk_aversion: float = 1.0
    depth: int = 2
    shots: int = 4096
    seed: int = 7


@app.exception_handler(service.InputError)
async def input_error(_: Request, e: service.InputError):
    return JSONResponse(status_code=400, content={"error": str(e)})


@app.exception_handler(RuntimeError)
async def runtime_error(_: Request, e: RuntimeError):
    return JSONResponse(status_code=503, content={"error": str(e)})


@app.exception_handler(Exception)
async def unexpected(_: Request, e: Exception):
    return JSONResponse(status_code=500, content={"error": "The computation failed unexpectedly. Check the backend log."})


def _qiskit_version():
    try:
        import qiskit
        return qiskit.__version__
    except ImportError:
        return None


@app.get("/api/health")
def health():
    return {"status": "ok", "qiskit": _qiskit_version()}


@app.get("/api/default-problem")
def default_problem():
    return service.default_payload()


@app.post("/api/validate")
def validate(p: ProblemIn):
    prob = service.problem_from_payload(p.model_dump())
    return {"valid": True, "assets": prob.n, "qubits": prob.n, "feasible_portfolios": __import__("math").comb(prob.n, prob.k)}


@app.post("/api/optimize")
def optimize(p: ProblemIn):
    return service.optimize(p.model_dump())


@app.post("/api/circuit")
def circuit(p: ProblemIn):
    return service.circuit_info(p.model_dump())


@app.post("/api/transpile")
def transpile(p: ProblemIn):
    return service.transpile_info(p.model_dump())

