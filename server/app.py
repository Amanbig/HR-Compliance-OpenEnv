"""
OpenEnv HR Compliance — FastAPI server

Serves the HTML frontend and exposes the REST API:
    GET  /           — HTML UI
    POST /reset      — initialise / reset the environment
    POST /step       — execute one action
    GET  /state      — return current environment state
    GET  /health     — liveness probe
    POST /api/load-task      — load a task for the UI
    POST /api/manual-step    — execute a user-supplied action (UI)
    POST /api/single-ai-step — one AI-driven step (UI)
    POST /api/full-episode   — run a complete AI episode (UI)
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path so `env`, `tasks`, etc. resolve
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from env import Action, HRComplianceEnv  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from src.config import API_BASE, API_KEY, MAX_AUTO_STEPS, MODEL, TASK_INFO  # noqa: E402
from src.helpers import (  # noqa: E402
    build_system_prompt,
    load_task_desc,
    make_openai_client,
    parse_action_json,
)

app = FastAPI(title="OpenEnv HR Compliance", version="1.0.0")

# Mount static files
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ── Shared state ────────────────────────────────────────────────────────

_env: Optional[HRComplianceEnv] = None
_task_id: Optional[int] = None


# ── Request schemas ─────────────────────────────────────────────────────


class ResetRequest(BaseModel):
    task_id: int = 1


class StepRequest(BaseModel):
    action_type: str
    item_id: str
    payload: Optional[str] = None


class AIStepRequest(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""


# ── HTML frontend ───────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = _STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text())


# ── Core REST API ───────────────────────────────────────────────────────


@app.post("/reset")
async def reset(req: ResetRequest = ResetRequest()):
    global _env, _task_id
    _env = HRComplianceEnv(req.task_id)
    _task_id = req.task_id
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


# ── UI API endpoints ───────────────────────────────────────────────────


@app.post("/api/load-task")
async def api_load_task(req: ResetRequest):
    global _env, _task_id
    tid = req.task_id
    _env = HRComplianceEnv(tid)
    _task_id = tid
    _env.reset()
    info = TASK_INFO.get(tid, {"name": "Unknown", "difficulty": "?"})
    desc = load_task_desc(tid)
    obs_data = _env._get_obs()
    return JSONResponse(
        content={
            "task_id": tid,
            "task_name": info["name"],
            "difficulty": info["difficulty"],
            "description": desc,
            "reports": [r.model_dump() for r in obs_data.reports],
            "current_folder": obs_data.current_folder,
        }
    )


@app.post("/api/manual-step")
async def api_manual_step(req: StepRequest):
    if _env is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Please load a task first."},
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


@app.post("/api/single-ai-step")
async def api_single_ai_step(req: AIStepRequest):
    if _env is None:
        return JSONResponse(
            status_code=400, content={"error": "Please load a task first."}
        )
    api_key = req.api_key or API_KEY
    base_url = req.base_url or API_BASE
    model_name = req.model or MODEL

    if not api_key:
        return JSONResponse(
            status_code=400,
            content={
                "error": "API key is missing. Set HF_TOKEN in Space secrets or enter it in Settings."
            },
        )
    if not base_url:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Base URL is missing. Set API_BASE_URL in Space secrets or enter it in Settings."
            },
        )

    obs = _env._get_obs()
    desc = load_task_desc(_task_id)
    client = make_openai_client(api_key, base_url)

    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": build_system_prompt(desc)},
                {
                    "role": "user",
                    "content": f"Current observation:\n{obs.model_dump_json()}",
                },
            ],
            temperature=0.2,
            max_tokens=300,
        )
    except Exception as exc:
        msg = str(exc)
        if "401" in msg or "auth" in msg.lower() or "token" in msg.lower():
            detail = f"Authentication failed — check your API key. Details: {msg}"
        elif "404" in msg:
            detail = (
                f"Model not found — check model name '{model_name}'. Details: {msg}"
            )
        elif "429" in msg or "rate" in msg.lower():
            detail = (
                f"Rate limited — too many requests, try again later. Details: {msg}"
            )
        else:
            detail = f"API call failed: {msg}"
        return JSONResponse(status_code=502, content={"error": detail})

    action_json = resp.choices[0].message.content or ""

    try:
        parsed = parse_action_json(action_json)
        action = Action(**parsed)
    except Exception as exc:
        return JSONResponse(
            status_code=422,
            content={
                "error": f"Model returned invalid action JSON: {exc}",
                "raw_response": action_json[:500],
            },
        )

    obs, reward, done, info = _env.step(action)

    return JSONResponse(
        content={
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info,
            "action": action.model_dump(),
            "action_json": action_json,
        }
    )


@app.post("/api/full-episode")
async def api_full_episode(req: AIStepRequest):
    global _env, _task_id
    if _task_id is None:
        return JSONResponse(
            status_code=400, content={"error": "Please load a task first."}
        )
    api_key = req.api_key or API_KEY
    base_url = req.base_url or API_BASE
    model_name = req.model or MODEL

    if not api_key:
        return JSONResponse(
            status_code=400,
            content={
                "error": "API key is missing. Set HF_TOKEN in Space secrets or enter it in Settings."
            },
        )
    if not base_url:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Base URL is missing. Set API_BASE_URL in Space secrets or enter it in Settings."
            },
        )

    _env = HRComplianceEnv(_task_id)
    _env.reset()
    obs = _env._get_obs()
    desc = load_task_desc(_task_id)
    info_t = TASK_INFO[_task_id]

    try:
        client = make_openai_client(api_key, base_url)
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"error": f"Failed to create API client: {exc}"},
        )

    messages = [{"role": "system", "content": build_system_prompt(desc)}]
    log_lines = [
        f"Task {_task_id}: {info_t['name']} ({info_t['difficulty']})",
        f"{desc.strip()}\n",
    ]
    final_score = 0.0
    final_step = MAX_AUTO_STEPS
    done = False

    for step_num in range(1, MAX_AUTO_STEPS + 1):
        messages.append(
            {
                "role": "user",
                "content": f"Step {step_num}/{MAX_AUTO_STEPS}. Current observation:\n{obs.model_dump_json(indent=2)}",
            }
        )
        try:
            resp = client.chat.completions.create(
                model=model_name, messages=messages, temperature=0.2, max_tokens=300
            )
            response_text = resp.choices[0].message.content or ""
        except Exception as exc:
            msg = str(exc)
            if "401" in msg or "auth" in msg.lower() or "token" in msg.lower():
                detail = f"Authentication failed — check your API key. ({msg})"
            elif "404" in msg:
                detail = f"Model '{model_name}' not found — check model name. ({msg})"
            elif "429" in msg or "rate" in msg.lower():
                detail = f"Rate limited — try again later. ({msg})"
            else:
                detail = f"API error: {msg}"
            log_lines.append(f"Step {step_num}: {detail}")
            break

        messages.append({"role": "assistant", "content": response_text})

        try:
            action = Action(**parse_action_json(response_text))
        except Exception:
            log_lines.append(f"Step {step_num}: Parse Error — Bad JSON")
            messages.append(
                {
                    "role": "user",
                    "content": "Invalid JSON. Output ONLY a valid JSON action object.",
                }
            )
            continue

        obs, reward, done, info = _env.step(action)
        final_score = info.get("score", 0.0)
        payload_str = f", '{action.payload}'" if action.payload else ""
        reason_short = reward.reason[:60] + ("..." if len(reward.reason) > 60 else "")
        log_lines.append(
            f"Step {step_num}: {action.action_type}({action.item_id}{payload_str}) "
            f"| reward={reward.value:.2f} | {reason_short}"
        )
        if done:
            final_step = step_num
            break

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Reward: {reward.value:.2f} | Progress: {reward.partial_progress:.2f} "
                    f"| Penalties: {reward.penalties:.2f} | {reward.reason}"
                ),
            }
        )

    outcome = "Completed" if done else "Max steps reached"
    log_lines.append(
        f"\n{outcome} — Steps: {final_step} | Final score: {final_score:.2f}"
    )

    final_obs = _env._get_obs()
    return JSONResponse(
        content={
            "task_id": _task_id,
            "task_name": info_t["name"],
            "score": final_score,
            "steps": final_step,
            "done": done,
            "observation": final_obs.model_dump(),
            "log": "\n".join(log_lines),
        }
    )


# ── Entry point ─────────────────────────────────────────────────────────


def main():
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
