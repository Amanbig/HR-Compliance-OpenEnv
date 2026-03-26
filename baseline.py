import os
import json
from openai import OpenAI
from env import HRComplianceEnv, Action
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def run_task(task_id, max_steps=10):
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o")

    # Local endpoints often don't require real keys, but the OpenAI client expects *something*
    if not api_key:
        if base_url:
            api_key = "dummy_key"
        else:
            print("OPENAI_API_KEY not found. Returning score 0.")
            return 0.0

    client = OpenAI(api_key=api_key, base_url=base_url)
    env = HRComplianceEnv(task_id)
    obs = env.reset()
    
    with open("openenv.yaml", "r") as f:
        meta = yaml.safe_load(f)
    task_desc = next((t['description'] for t in meta['tasks'] if t['id'] == task_id), "")
    
    system_prompt = f"""You are an AI HR Compliance Officer. Your task: {task_desc}
You can take actions by outputting JSON matching this Pydantic schema:
Action(action_type: Literal['read', 'reply', 'move', 'delete', 'tag'], item_id: str, payload: Optional[str])

Available actions:
- read: marks report as read. item_id is required. payload is null.
- reply: payload should contain the reply body.
- move: payload should contain the destination folder name.
- delete: moves to trash.
- tag: payload should contain the tag string.

Output ONLY JSON. Output exactly a dictionary that fits the Action model.
Example: {{"action_type": "read", "item_id": "101", "payload": null}}
"""
    msgs = [{"role": "system", "content": system_prompt}]
    
    for step_idx in range(max_steps):
        msgs.append({"role": "user", "content": f"Observation: {obs.model_dump_json()}"})
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=msgs,
                response_format={ "type": "json_object" }
            )
            action_json = resp.choices[0].message.content
            msgs.append({"role": "assistant", "content": action_json})
            
            action_dict = json.loads(action_json)
            action = Action(**action_dict)
            
            obs, reward, done, info = env.step(action)
            
            if done:
                print(f"Task {task_id} completed. Score: {info.get('score', 0)}")
                return info.get('score', 0)
        except Exception as e:
            print(f"Error calling API for task {task_id}: {e}")
            break
            
    print(f"Task {task_id} incomplete after {max_steps} steps.")
    return 0.0

if __name__ == "__main__":
    scores = []
    print("Running baselines...")
    for i in range(1, 4):
        s = run_task(i)
        scores.append(s)
    
    print(f"Baseline Scores (Tasks 1, 2, 3): {scores}")
