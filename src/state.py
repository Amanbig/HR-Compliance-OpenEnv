"""
src/state.py — Gradio UI environment state management.

Holds the single env instance used by Gradio handlers.
The REST API (server/app.py) manages its own separate env instance.
"""

from typing import Optional
from env import HRComplianceEnv

# Module-level state — one env per active UI session
_env: Optional[HRComplianceEnv] = None
_task_id: Optional[int] = None


def get_env() -> Optional[HRComplianceEnv]:
    return _env


def get_task_id() -> Optional[int]:
    return _task_id


def init_env(task_id: int) -> HRComplianceEnv:
    """Create a fresh env for the given task and persist it."""
    global _env, _task_id
    _env = HRComplianceEnv(task_id)
    _env.reset()
    _task_id = task_id
    return _env


def reset_env() -> Optional[HRComplianceEnv]:
    """Reset the current env to its initial state (same task)."""
    global _env
    if _env is not None:
        _env.reset()
    return _env
