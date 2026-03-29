"""
app.py — HF Space entry point.

Uses demo.launch() (the canonical HF Spaces approach) so HF's readiness
probe passes correctly. REST routes are added to Gradio's internal FastAPI
app (demo.app) before launch, which Gradio 5+ preserves through launch().
"""

from typing import Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from env import Action, HRComplianceEnv
from src.ui import demo  # Gradio Blocks (also imports src.config, etc.)

# ── Shared REST state ─────────────────────────────────────────────────────────

_env: Optional[HRComplianceEnv] = None


# ── Request schemas ───────────────────────────────────────────────────────────


class ResetRequest(BaseModel):
    task_id: int = 1


class StepRequest(BaseModel):
    action_type: str
    item_id: str
    payload: Optional[str] = None


# ── REST endpoints on Gradio's internal FastAPI app ───────────────────────────
# demo.app lazily creates and caches the FastAPI instance (Gradio 5+).
# demo.launch() reuses that same instance, so routes added here persist.

_api = demo.app


@_api.post("/reset")
async def reset(req: ResetRequest = ResetRequest()):
    global _env
    _env = HRComplianceEnv(req.task_id)
    obs = _env.reset()
    return JSONResponse(
        content={"observation": obs.model_dump(), "info": {"task_id": req.task_id}}
    )


@_api.post("/step")
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


@_api.get("/state")
async def state():
    if _env is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Environment not initialised. Call POST /reset first."},
        )
    return JSONResponse(content=_env.state())


@_api.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False,
    )
