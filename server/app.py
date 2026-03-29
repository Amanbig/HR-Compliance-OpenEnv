"""
OpenEnv HR Compliance — FastAPI server
Exposes the standard OpenEnv REST API:
    POST /reset   — initialise / reset the environment (body: {"task_id": 1-5})
    POST /step    — execute one action (see action_type values below)
    GET  /state   — return current environment state
    GET  /health  — liveness probe

Supported action_type values:
    read, reply, move, delete, tag, escalate, flag, assign, close
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from env import HRComplianceEnv, Action

app = FastAPI(title="OpenEnv HR Compliance", version="1.0.0")

_env: Optional[HRComplianceEnv] = None


# ── Request schemas ──────────────────────────────────────────────────────


class ResetRequest(BaseModel):
    task_id: int = 1


class StepRequest(BaseModel):
    action_type: str
    item_id: str
    payload: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────


@app.post("/reset")
async def reset(req: ResetRequest = ResetRequest()):
    global _env
    _env = HRComplianceEnv(req.task_id)
    obs = _env.reset()
    return JSONResponse(
        content={
            "observation": obs.model_dump(),
            "info": {"task_id": req.task_id},
        }
    )


@app.post("/step")
async def step(req: StepRequest):
    if _env is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Environment not initialised. Call POST /reset first."},
        )
    action = Action(
        action_type=req.action_type, item_id=req.item_id, payload=req.payload
    )
    obs, reward, done, info = _env.step(action)
    return JSONResponse(
        content={
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info,
        }
    )


@app.get("/state")
async def state():
    if _env is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Environment not initialised. Call POST /reset first."},
        )
    return JSONResponse(content=_env.state())


@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})


# ── Entry point ──────────────────────────────────────────────────────────


def main():
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
