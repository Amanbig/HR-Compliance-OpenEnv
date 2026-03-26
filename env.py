from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

class Email(BaseModel):
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
    emails: List[Email]
    current_folder: str

class Action(BaseModel):
    action_type: Literal['read', 'reply', 'move', 'delete', 'tag']
    email_id: str
    payload: Optional[str] = None

class Reward(BaseModel):
    value: float
    partial_progress: float
    penalties: float
    reason: str

class EmailTriageEnv:
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.state_data = {}
        self.history = []
        self.reset()
    
    def reset(self) -> Observation:
        from tasks import get_task_emails
        self.state_data['emails'] = get_task_emails(self.task_id)
        self.state_data['current_folder'] = "inbox"
        self.history = []
        return self._get_obs()

    def state(self) -> Dict[str, Any]:
        return {
            "emails": [e.model_dump() for e in self.state_data['emails']],
            "current_folder": self.state_data['current_folder'],
            "history": self.history
        }
        
    def _get_obs(self) -> Observation:
        return Observation(
            emails=[e for e in self.state_data['emails'] if e.folder == self.state_data['current_folder']],
            current_folder=self.state_data['current_folder']
        )
        
    def step(self, action: Action):
        email = next((e for e in self.state_data['emails'] if e.id == action.email_id), None)
        
        reward_value = 0.0
        partial = 0.0
        penalty = 0.0
        reason = ""
        done = False
        
        if not email:
            penalty += 0.1
            reason = "Email ID not found."
        else:
            if action.action_type == 'read':
                if not email.read:
                    email.read = True
                    partial += 0.1
                    reason = f"Read email {email.id}."
                else:
                    penalty += 0.05
                    reason = f"Email {email.id} already read."
            elif action.action_type == 'tag':
                if action.payload and action.payload not in email.tags:
                    email.tags.append(action.payload)
                    partial += 0.2
                    reason = f"Tagged email {email.id} with {action.payload}."
                else:
                    penalty += 0.05
                    reason = "Tag already exists or no payload."
            elif action.action_type == 'move':
                if action.payload:
                    email.folder = action.payload
                    reason = f"Moved email {email.id} to {action.payload}."
                else:
                    penalty += 0.1
                    reason = "Move action requires a payload (folder name)."
            elif action.action_type == 'delete':
                email.folder = 'trash'
                reason = f"Deleted email {email.id}."
            elif action.action_type == 'reply':
                if action.payload:
                    email.replied = True
                    email.reply_body = action.payload
                    reason = f"Replied to email {email.id}."
                    partial += 0.5
                else:
                    penalty += 0.1
                    reason = "Reply requires a payload."
                    
        self.history.append({'action': action.model_dump(), 'reason': reason})
        
        from tasks import score_task
        score, done_reason, task_done = score_task(self.task_id, self.state_data['emails'], action, self.history)
        
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
