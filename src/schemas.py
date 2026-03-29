"""
src/schemas.py — Pydantic request/response schemas for the Gradio UI layer.

Note: Core environment schemas (Observation, Action, Reward, Report)
live in env.py. These are UI-layer-specific schemas only.
"""

from typing import Optional
from pydantic import BaseModel


# ── Request schemas ───────────────────────────────────────────────────────────


class LoadTaskRequest(BaseModel):
    """Request to load and initialise a task by ID."""

    task_id: int


class ManualStepRequest(BaseModel):
    """A manually entered JSON action submitted from the UI."""

    action_type: str
    item_id: str
    payload: Optional[str] = None


# ── Response / result schemas ─────────────────────────────────────────────────


class StepResult(BaseModel):
    """Structured result of a single environment step, ready for UI rendering."""

    status: str
    reports_md: str
    details_md: str
    score_str: str
    log: str
    action_json: str = ""


class EpisodeResult(BaseModel):
    """Structured result of a full multi-step episode."""

    status: str
    reports_md: str
    details_md: str
    score_str: str
    log: str
    steps_taken: int
    final_score: float
