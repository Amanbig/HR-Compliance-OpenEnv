---
title: HR Compliance OpenEnv
emoji: 🏢
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
tags:
  - openenv
---

# OpenEnv: HR Compliance Review

## Description & Motivation

The **HR Compliance Review** environment simulates the work of a corporate HR compliance officer — a sensitive, high-stakes real-world role. Agents must triage incoming employee reports, route IT requests, escalate workplace safety violations, handle legal threats, and identify whistleblower complaints and multi-report harassment patterns, all while filtering out noise and false positives.

This domain is valuable for evaluating AI agents because it requires:
- **Reading comprehension** — understanding intent behind employee reports
- **Classification under ambiguity** — distinguishing real hazards from deceptive language
- **Multi-step reasoning** — reading, then deciding, then acting across multiple steps
- **Pattern recognition** — correlating multiple reports from the same victim (Task 5)
- **Restraint** — knowing when NOT to act (ignoring gossip, avoiding false escalations)

---

## Action Space

Agents output one JSON action per step:

```python
class Action(BaseModel):
    action_type: Literal[
        "read",      # Mark report as read
        "reply",     # Send reply (payload = reply text)
        "move",      # Move to folder (payload = folder name)
        "delete",    # Move to trash
        "tag",       # Add tag (payload = tag string)
        "escalate",  # Escalate to team (payload = "Legal" | "Security" | "HR_Investigation" | "Management")
        "flag",      # Set priority (payload = "urgent" | "high" | "normal")
        "assign",    # Assign ownership (payload = team or person name)
        "close",     # Resolve and close report
    ]
    item_id: str
    payload: Optional[str] = None
```

| Action | Payload | Effect |
|--------|---------|--------|
| `read` | — | Mark as read |
| `reply` | Reply text | Send reply to sender |
| `move` | Folder name | Move to folder (e.g. `IT_Support`, `Confidential`) |
| `delete` | — | Move to trash |
| `tag` | Tag string | Add tag (e.g. `safety_hazard`, `investigation_required`) |
| `escalate` | Team name | Escalate to specialist team, moves to `Escalated` folder |
| `flag` | `urgent` / `high` / `normal` | Set priority level |
| `assign` | Assignee name | Assign report to team or person |
| `close` | — | Resolve and close report |

---

## Observation Space

```python
class Observation(BaseModel):
    reports: List[Report]     # Reports in the current folder
    current_folder: str       # Active folder name

class Report(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    folder: str               # inbox | IT_Support | Confidential | Escalated | trash
    tags: List[str]
    read: bool
    replied: bool
    reply_body: Optional[str]
    priority: str             # normal | high | urgent
    escalated_to: Optional[str]
    assigned_to: Optional[str]
    closed: bool
```

---

## Reward Function

```python
class Reward(BaseModel):
    value: float          # Blended score (0.0–1.0): task progress + step signal
    partial_progress: float  # Points earned this step for useful actions
    penalties: float      # Deductions for invalid or redundant actions
    reason: str           # Human-readable feedback
```

- Rewards are **continuous** — every useful action earns partial credit
- Penalties for invalid IDs, duplicate reads, missing payloads
- Final `value` on task completion is the authoritative grader score

---

## Evaluation Tasks

| # | Task | Difficulty | Objective |
|---|------|------------|-----------|
| 1 | IT Ticket Routing | Easy | Move IT support messages to `IT_Support` folder |
| 2 | Workplace Safety Violations | Medium | Tag genuine hazards `safety_hazard` + reply; no false positives |
| 3 | Whistleblower Escalation | Hard | Move embezzlement report to `Confidential`, tag `investigation_required` |
| 4 | Legal Threat Routing | Medium-Hard | `escalate` genuine legal threats to `Legal` team; ignore venting |
| 5 | Harassment Pattern Detection | Hard | Identify 3 reports from same victim, `flag` as `urgent` + `assign` to `HR_Investigation` |

**Difficulty progression:**
- **Easy** — straightforward keyword matching
- **Medium** — distinguishing real hazards from figurative language
- **Hard** — one needle in ten reports; resist multiple distractors
- **Medium-Hard** — legal intent vs emotional venting
- **Hard** — cross-report pattern recognition (same victim, same harasser)

---

## REST API Endpoints

The HF Space exposes a standard OpenEnv REST API alongside the Gradio UI:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reset` | Initialise environment. Body: `{"task_id": 1}` |
| `POST` | `/step` | Execute action. Body: `{"action_type": "read", "item_id": "IT-101", "payload": null}` |
| `GET` | `/state` | Return full environment state |
| `GET` | `/health` | Liveness probe |

---

## Setup & Usage

### Prerequisites

```bash
pip install uv
uv pip install -e .
```

### Running the Inference Script

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
export HF_TOKEN="hf_..."

python inference.py
```

### Running the Web UI

```bash
python app.py
# Open http://localhost:7860
```

### Docker

```bash
docker build -t openenv-hr-compliance .
docker run -p 7860:7860 openenv-hr-compliance
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_BASE_URL` | Yes | LLM API endpoint |
| `MODEL_NAME` | Yes | Model identifier for inference |
| `HF_TOKEN` | Yes | Hugging Face API token |

---

## Baseline Scores

Scores from `inference.py` with `meta-llama/Llama-3.3-70B-Instruct`:

| Task | Score |
|------|-------|
| 1 — IT Ticket Routing | 1.00 |
| 2 — Safety Violations | 1.00 |
| 3 — Whistleblower Escalation | 1.00 |
| 4 — Legal Threat Routing | ~0.5–1.0 |
| 5 — Harassment Pattern | ~0.5–1.0 |

---

## Project Structure

```
.
├── app.py              # Entry point: mounts Gradio UI onto FastAPI (15 lines)
├── env.py              # Core environment: Report, Observation, Action, Reward, HRComplianceEnv
├── tasks.py            # Task generation (Faker) + deterministic graders
├── inference.py        # Baseline inference script (API_BASE_URL / MODEL_NAME / HF_TOKEN)
│
├── src/
│   ├── config.py       # Constants: API creds, TASK_INFO, CSS
│   ├── schemas.py      # Pydantic UI schemas: LoadTaskRequest, StepResult, EpisodeResult
│   ├── helpers.py      # Pure utils: format, parse, build prompts, OpenAI client
│   ├── state.py        # Gradio env state management
│   ├── handlers.py     # Gradio event handlers (4 functions)
│   └── ui.py           # Gradio Blocks layout + event wiring
│
├── server/
│   └── app.py          # FastAPI REST API: /reset /step /state /health
│
├── openenv.yaml        # OpenEnv metadata, task specs, action/observation schemas
├── Dockerfile          # Container config
└── pyproject.toml      # Dependencies + [project.scripts] entry point
```
