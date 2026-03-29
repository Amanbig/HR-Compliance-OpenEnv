"""
src/helpers.py — Pure, stateless utility functions.
No side effects. Safe to import anywhere.
"""

import json

import yaml
from openai import OpenAI


# ── Task metadata ─────────────────────────────────────────────────────────────


def load_task_desc(task_id: int, yaml_path: str = "openenv.yaml") -> str:
    """Return the task description string from openenv.yaml."""
    with open(yaml_path, "r") as f:
        meta = yaml.safe_load(f)
    return next(
        (t["description"] for t in meta["tasks"] if t["id"] == task_id),
        "Unknown task",
    )


# ── LLM helpers ───────────────────────────────────────────────────────────────


def build_system_prompt(task_desc: str) -> str:
    """Build the HR Compliance Officer system prompt for the agent."""
    return f"""You are an AI HR Compliance Officer. Your task: {task_desc}
Output a single JSON action per response:
{{"action_type": "<type>", "item_id": "<report id>", "payload": "<string or null>"}}

Action types and payloads:
- read      → payload: null
- reply     → payload: reply text
- move      → payload: folder name  (e.g. "IT_Support", "Confidential")
- delete    → payload: null
- tag       → payload: tag string   (e.g. "safety_hazard", "investigation_required")
- escalate  → payload: team name    (e.g. "Legal", "Security", "HR_Investigation")
- flag      → payload: "urgent" | "high" | "normal"
- assign    → payload: team/person  (e.g. "HR_Investigation")
- close     → payload: null

Strategy: read reports first, then act. One action per step.
Output ONLY valid JSON. No explanation."""


def parse_action_json(text: str) -> dict:
    """Parse a JSON action from a model response, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = [
            line for line in text.split("\n") if not line.strip().startswith("```")
        ]
        text = "\n".join(lines).strip()
    return json.loads(text)


def make_openai_client(api_key: str, base_url: str) -> OpenAI:
    """Construct an OpenAI client from the given credentials."""
    return OpenAI(
        api_key=api_key or "dummy_key",
        base_url=base_url or None,
    )


# ── Observation formatting ────────────────────────────────────────────────────


def format_reports_md(obs) -> str:
    """Render the observation's report list as a markdown table."""
    if not obs.reports:
        return "*No reports in this folder.*"
    rows = [
        "| ID | Sender | Subject | Tags | Priority | Read | Replied |",
        "|:---|:-------|:--------|:-----|:--------:|:----:|:-------:|",
    ]
    for r in obs.reports:
        tags = ", ".join(r.tags) if r.tags else "—"
        priority = f"**{r.priority}**" if r.priority != "normal" else r.priority
        rows.append(
            f"| `{r.id}` | {r.sender} | **{r.subject}** "
            f"| {tags} | {priority} "
            f"| {'Yes' if r.read else '—'} | {'Yes' if r.replied else '—'} |"
        )
    return "\n".join(rows)


def format_report_details(obs) -> str:
    """Render full report bodies with metadata as markdown."""
    if not obs.reports:
        return ""
    parts = []
    for r in obs.reports:
        meta_bits = []
        if r.priority != "normal":
            meta_bits.append(f"Priority: **{r.priority}**")
        if r.escalated_to:
            meta_bits.append(f"Escalated to: `{r.escalated_to}`")
        if r.assigned_to:
            meta_bits.append(f"Assigned to: `{r.assigned_to}`")
        meta_line = "  |  ".join(meta_bits)
        parts.append(
            f"**[{r.id}] {r.subject}**\n"
            f"From: `{r.sender}`"
            + (f"\n{meta_line}" if meta_line else "")
            + f"\n> {r.body}\n"
        )
    return "\n---\n".join(parts)


def wrap_score_html(score_str: str) -> str:
    """Wrap a score string in the styled HTML score display block."""
    return (
        f"<div class='score-display'>{score_str}</div>"
        f"<div class='score-label'>current score</div>"
    )
