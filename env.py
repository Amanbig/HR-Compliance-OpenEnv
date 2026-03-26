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

class Observation(BaseModel):
    reports: List[Report]
    current_folder: str

class Action(BaseModel):
    action_type: Literal['read', 'reply', 'move', 'delete', 'tag']
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
        self.state_data = {}
        self.history = []
        self.reset()
    
    def reset(self) -> Observation:
        from tasks import get_task_reports
        self.state_data['reports'] = get_task_reports(self.task_id)
        self.state_data['current_folder'] = "inbox"
        self.history = []
        return self._get_obs()

    def state(self) -> Dict[str, Any]:
        return {
            "reports": [e.model_dump() for e in self.state_data['reports']],
            "current_folder": self.state_data['current_folder'],
            "history": self.history
        }
        
    def _get_obs(self) -> Observation:
        return Observation(
            reports=[e for e in self.state_data['reports'] if e.folder == self.state_data['current_folder']],
            current_folder=self.state_data['current_folder']
        )
        
    def step(self, action: Action):
        report = next((e for e in self.state_data['reports'] if e.id == action.item_id), None)
        
        reward_value = 0.0
        partial = 0.0
        penalty = 0.0
        reason = ""
        done = False
        
        if not report:
            penalty += 0.1
            reason = "Item ID not found."
        else:
            if action.action_type == 'read':
                if not report.read:
                    report.read = True
                    partial += 0.1
                    reason = f"Read report {report.id}."
                else:
                    penalty += 0.05
                    reason = f"Report {report.id} already read."
            elif action.action_type == 'tag':
                if action.payload and action.payload not in report.tags:
                    report.tags.append(action.payload)
                    partial += 0.2
                    reason = f"Tagged report {report.id} with '{action.payload}'."
                else:
                    penalty += 0.05
                    reason = "Tag already exists or no payload."
            elif action.action_type == 'move':
                if action.payload:
                    report.folder = action.payload
                    reason = f"Moved report {report.id} to '{action.payload}' folder."
                else:
                    penalty += 0.1
                    reason = "Move action requires a payload (folder name)."
            elif action.action_type == 'delete':
                report.folder = 'trash'
                reason = f"Deleted report {report.id}."
            elif action.action_type == 'reply':
                if action.payload:
                    report.replied = True
                    report.reply_body = action.payload
                    reason = f"Replied to report {report.id}."
                    partial += 0.5
                else:
                    penalty += 0.1
                    reason = "Reply requires a payload."
                    
        self.history.append({'action': action.model_dump(), 'reason': reason})
        
        from tasks import score_task
        score, done_reason, task_done = score_task(self.task_id, self.state_data['reports'], action, self.history)
        
        if task_done:
            done = True
            reward_value = score
            reason += f" Task completed. {done_reason}"
            
        reward = Reward(
            value=reward_value,
            partial_progress=partial,
            penalties=penalty,
            reason=reason
        )
        
        return self._get_obs(), reward, done, {"score": score}
