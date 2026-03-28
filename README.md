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

## Environment Description & Motivation

The **HR Compliance Review** environment simulates the work of a corporate HR compliance officer — a sensitive, high-stakes real-world task. Agents must triage incoming employee reports, route IT requests, escalate workplace safety violations, and identify whistleblower complaints about financial misconduct, all while carefully filtering out office gossip and avoiding false positives.

This domain is valuable for evaluating AI agents because it requires:
- **Reading comprehension** — understanding report content and intent
- **Classification under ambiguity** — distinguishing genuine hazards from deceptive false positives
- **Multi-step reasoning** — reading, then deciding, then acting
- **Restraint** — knowing when NOT to act (ignoring gossip, avoiding false escalations)

## Action Space

Agents output one JSON action per step:

```python
class Action(BaseModel):
    action_type: Literal['read', 'reply', 'move', 'delete', 'tag']
    item_id: str               # Report ID to act on
    payload: Optional[str]     # Folder name, tag string, reply text, or null
```

| Action | Payload | Effect |
|--------|---------|--------|
| `read` | — | Marks report as read |
| `reply` | Reply text | Sends reply to report sender |
| `move` | Folder name | Moves report to specified folder |
| `delete` | — | Moves report to trash |
| `tag` | Tag string | Adds tag to report |

## Observation Space

Each step returns the current folder view:

```python
class Observation(BaseModel):
    reports: List[Report]      # Reports in the current folder
    current_folder: str        # Active folder name

class Report(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    folder: str
    tags: List[str]
    read: bool
    replied: bool
    reply_body: Optional[str]
```

## Reward Function

The reward provides **continuous signal** across the trajectory:

```python
class Reward(BaseModel):
    value: float               # Blended score (0.0-1.0): task progress + step signal
    partial_progress: float    # Points earned this step for useful actions
    penalties: float           # Deductions for invalid/redundant actions
    reason: str                # Human-readable feedback
```

- **Partial progress** rewards reading, tagging, moving, and replying
- **Penalties** for invalid IDs, redundant reads, missing payloads
- **Final score** is the authoritative task grader score (0.0-1.0)

## Evaluation Tasks

| # | Task | Difficulty | Objective | Perfect Score Criteria |
|---|------|------------|-----------|----------------------|
| 1 | IT Ticket Routing | Easy | Move IT support messages to `IT_Support` folder | All IT tickets routed correctly, no false routing |
| 2 | Workplace Safety Violations | Medium | Tag genuine hazards with `safety_hazard` and reply | All hazards tagged + replied, zero false positives |
| 3 | Whistleblower Escalation | Hard | Move embezzlement report to `Confidential`, tag `investigation_required` | Correct move + tag, no gossip escalated |

**Difficulty progression:**
- **Easy** — straightforward keyword matching (IT issues are obvious)
- **Medium** — requires distinguishing real hazards from deceptive language (e.g., "spilled coffee on shirt" vs. "chemical spill in sector A3")
- **Hard** — requires identifying one critical report among 10, resisting multiple gossip distractors

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

## Baseline Scores

Scores from running `inference.py` with `meta-llama/Llama-3.3-70B-Instruct`:

| Task | Score |
|------|-------|
| 1 (Easy) | ~1.0 |
| 2 (Medium) | ~0.5-1.0 |
| 3 (Hard) | ~0.5-1.0 |

*Scores vary due to procedural report generation and model stochasticity.*

## Project Structure

```
.
├── inference.py       # Baseline inference script (required)
├── env.py             # Environment: Observation, Action, Reward, HRComplianceEnv
├── tasks.py           # Task definitions, report generation, scoring/grading
├── app.py             # Gradio web UI
├── openenv.yaml       # OpenEnv metadata and task definitions
├── Dockerfile         # Container configuration
├── pyproject.toml     # Python dependencies
└── README.md          # This file
```
