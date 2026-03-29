"""
src/config.py — Application-wide constants and configuration.
"""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ── API credentials ───────────────────────────────────────────────────────────

API_KEY: str = (
    os.environ.get("HF_TOKEN")
    or os.environ.get("API_KEY")
    or os.environ.get("OPENAI_API_KEY", "")
)
API_BASE: str = os.environ.get("API_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "")
MODEL: str = os.environ.get("MODEL_NAME") or os.environ.get(
    "OPENAI_MODEL", "meta-llama/Llama-3.3-70B-Instruct"
)

# ── Episode settings ──────────────────────────────────────────────────────────

MAX_AUTO_STEPS: int = 15

# ── Task metadata ─────────────────────────────────────────────────────────────

TASK_INFO: dict = {
    1: {"name": "IT Ticket Routing", "difficulty": "Easy", "color": "#22c55e"},
    2: {
        "name": "Workplace Safety Violations",
        "difficulty": "Medium",
        "color": "#f59e0b",
    },
    3: {"name": "Whistleblower Escalation", "difficulty": "Hard", "color": "#ef4444"},
    4: {
        "name": "Legal Threat Routing",
        "difficulty": "Medium-Hard",
        "color": "#8b5cf6",
    },
    5: {
        "name": "Harassment Pattern Detection",
        "difficulty": "Hard",
        "color": "#dc2626",
    },
}

# ── UI styles ─────────────────────────────────────────────────────────────────

CSS: str = """
.main-header { text-align: center; padding: 1.5rem 0 0.5rem 0; }
.main-header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }
.main-header p  { color: #6b7280; font-size: 0.95rem; }
.score-display  { font-size: 2.5rem; font-weight: 800; text-align: center;
                  padding: 0.5rem; font-family: monospace; }
.score-label    { text-align: center; color: #6b7280; font-size: 0.85rem; }
footer          { display: none !important; }
"""
