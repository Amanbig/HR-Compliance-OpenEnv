from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field


class Report(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    folder: str = "inbox"
    tags: List[str] = Field(default_factory=list)
    read: bool = False
    replied: bool = False
    reply_body: Optional[str] = None
    # Extended fields for richer action space
    priority: str = "normal"  # normal | high | urgent
    escalated_to: Optional[str] = None  # team the report was escalated to
    assigned_to: Optional[str] = None  # person/team assigned
    closed: bool = False  # resolved/closed


class Observation(BaseModel):
    reports: List[Report]
    current_folder: str


class Action(BaseModel):
    action_type: Literal[
        "read",  # Mark as read
        "reply",  # Send a reply (payload = reply text)
        "move",  # Move to folder (payload = folder name)
        "delete",  # Move to trash
        "tag",  # Add a tag (payload = tag string)
        "escalate",  # Escalate to a team (payload = team: Legal/Security/HR_Investigation/Management)
        "flag",  # Set priority (payload = urgent | high | normal)
        "assign",  # Assign to a team/person (payload = assignee name)
        "close",  # Resolve and close the report
    ]
    item_id: str
    payload: Optional[str] = None


class Reward(BaseModel):
    value: float
    partial_progress: float
    penalties: float
    reason: str


class HRComplianceEnv:
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.state_data: Dict[str, Any] = {}
        self.history: list = []
        self.cumulative_progress: float = 0.0
        self.cumulative_penalty: float = 0.0
        self.reset()

    def reset(self) -> Observation:
        from tasks import get_task_reports

        reports, gt = get_task_reports(self.task_id)
        self.state_data["reports"] = reports
        self.state_data["ground_truth"] = gt
        self.state_data["current_folder"] = "inbox"
        self.history = []
        self.cumulative_progress = 0.0
        self.cumulative_penalty = 0.0
        return self._get_obs()

    def state(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "reports": [e.model_dump() for e in self.state_data["reports"]],
            "current_folder": self.state_data["current_folder"],
            "history": self.history,
            "cumulative_progress": self.cumulative_progress,
            "cumulative_penalty": self.cumulative_penalty,
        }

    def _get_obs(self) -> Observation:
        return Observation(
            reports=[
                e
                for e in self.state_data["reports"]
                if e.folder == self.state_data["current_folder"]
            ],
            current_folder=self.state_data["current_folder"],
        )

    def step(self, action: Action):
        report = next(
            (e for e in self.state_data["reports"] if e.id == action.item_id), None
        )

        partial = 0.0
        penalty = 0.0
        reason = ""
        done = False

        if not report:
            penalty += 0.1
            reason = "Item ID not found."
        else:
            if action.action_type == "read":
                if not report.read:
                    report.read = True
                    partial += 0.1
                    reason = f"Read report {report.id}."
                else:
                    penalty += 0.05
                    reason = f"Report {report.id} already read."

            elif action.action_type == "tag":
                if action.payload and action.payload not in report.tags:
                    report.tags.append(action.payload)
                    partial += 0.2
                    reason = f"Tagged report {report.id} with '{action.payload}'."
                else:
                    penalty += 0.05
                    reason = "Tag already exists or no payload."

            elif action.action_type == "move":
                if action.payload:
                    report.folder = action.payload
                    partial += 0.15
                    reason = f"Moved report {report.id} to '{action.payload}' folder."
                else:
                    penalty += 0.1
                    reason = "Move action requires a payload (folder name)."

            elif action.action_type == "delete":
                report.folder = "trash"
                reason = f"Deleted report {report.id}."

            elif action.action_type == "reply":
                if action.payload:
                    report.replied = True
                    report.reply_body = action.payload
                    partial += 0.3
                    reason = f"Replied to report {report.id}."
                else:
                    penalty += 0.1
                    reason = "Reply requires a payload (reply text)."

            elif action.action_type == "escalate":
                if action.payload:
                    report.escalated_to = action.payload
                    report.folder = "Escalated"
                    partial += 0.25
                    reason = f"Escalated report {report.id} to '{action.payload}'."
                else:
                    penalty += 0.1
                    reason = "Escalate requires a payload (team name)."

            elif action.action_type == "flag":
                valid = {"urgent", "high", "normal"}
                if action.payload and action.payload.lower() in valid:
                    report.priority = action.payload.lower()
                    partial += 0.15
                    reason = (
                        f"Flagged report {report.id} as '{action.payload}' priority."
                    )
                else:
                    penalty += 0.05
                    reason = f"Flag payload must be one of: {', '.join(sorted(valid))}."

            elif action.action_type == "assign":
                if action.payload:
                    report.assigned_to = action.payload
                    partial += 0.2
                    reason = f"Assigned report {report.id} to '{action.payload}'."
                else:
                    penalty += 0.1
                    reason = "Assign requires a payload (assignee name or team)."

            elif action.action_type == "close":
                if not report.closed:
                    report.closed = True
                    partial += 0.1
                    reason = f"Closed report {report.id}."
                else:
                    penalty += 0.05
                    reason = f"Report {report.id} is already closed."

        self.cumulative_progress += partial
        self.cumulative_penalty += penalty
        self.history.append({"action": action.model_dump(), "reason": reason})

        from tasks import score_task

        score, done_reason, task_done = score_task(
            self.task_id,
            self.state_data["reports"],
            action,
            self.history,
            self.state_data.get("ground_truth", {}),
        )

        # Blended reward: task-level progress + step-level partial/penalty signal
        reward_value = max(0.0, min(1.0, score + partial - penalty))

        if task_done:
            done = True
            reward_value = score
            reason += f" Task completed. {done_reason}"

        reward = Reward(
            value=reward_value,
            partial_progress=partial,
            penalties=penalty,
            reason=reason,
        )

        return self._get_obs(), reward, done, {"score": score}
