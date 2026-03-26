import gradio as gr
import json
import os
import yaml
from env import HRComplianceEnv, Action
from openai import OpenAI

env = None
current_task_id = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def init_env(task_id):
    global env, current_task_id
    try:
        task_id_int = int(task_id)
        current_task_id = task_id_int
        env = HRComplianceEnv(task_id_int)
        obs = env.reset()
        
        with open("openenv.yaml", "r") as f:
            meta = yaml.safe_load(f)
        task_desc = next((t['description'] for t in meta['tasks'] if t['id'] == task_id_int), "Unknown task")
            
        return f"Environment loaded for Task {task_id_int} - {task_desc}.\n\nObservation:\n{obs.model_dump_json(indent=2)}"
    except Exception as e:
        return f"Failed to initialize: {e}"

def step_env(action_str):
    global env
    if not env:
        return "Please initialize the environment first."
        
    if not action_str or not action_str.strip():
        return 'Error: Action JSON cannot be empty. Please provide a valid JSON string (e.g. {"action_type": "read", "item_id": "101", "payload": null})'
    
    try:
        action_dict = json.loads(action_str)
        action = Action(**action_dict)
        obs, reward, done, info = env.step(action)
        return f"Observation:\n{obs.model_dump_json(indent=2)}\n\nReward:\n{reward.model_dump_json(indent=2)}\n\nDone: {done}\n\nInfo: {info}"
    except Exception as e:
        return f"Error executing step: {str(e)}"

def auto_step_env(api_key, base_url, model_name):
    global env, current_task_id
    if not env:
        return "Please initialize the environment first.", ""
        
    if not api_key and not base_url:
        return "Error: Please provide an API Key or Base URL in the Settings.", ""

    try:
        with open("openenv.yaml", "r") as f:
            meta = yaml.safe_load(f)
        task_desc = next((t['description'] for t in meta['tasks'] if t['id'] == current_task_id), "")
        
        system_prompt = f"""You are an AI HR Compliance Officer. Your task: {task_desc}
You can take actions by outputting JSON matching this Pydantic schema:
Action(action_type: Literal['read', 'reply', 'move', 'delete', 'tag'], item_id: str, payload: Optional[str])

Available actions:
- read: marks report as read. item_id is required. payload is null.
- reply: payload should contain the reply body.
- move: payload should contain the destination folder name.
- delete: moves to trash.
- tag: payload should contain the tag string.

Output ONLY JSON. Output exactly a dictionary that fits the Action model."""

        obs = env._get_obs()
        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Observation: {obs.model_dump_json()}"}
        ]
        
        client = OpenAI(
            api_key=api_key if api_key else "dummy_key", 
            base_url=base_url if base_url else None
        )
        
        resp = client.chat.completions.create(
            model=model_name if model_name else "gpt-4o",
            messages=msgs,
            response_format={ "type": "json_object" }
        )
        
        action_json = resp.choices[0].message.content
        
        step_result = step_env(action_json)
        
        return step_result, action_json
        
    except Exception as e:
        return f"Error during AI Auto-Step: {str(e)}", ""

with gr.Blocks(title="OpenEnv - HR Compliance") as demo:
    gr.Markdown("# HR Compliance Review Environment")
    gr.Markdown("Simulate actions as an HR compliance officer interacting with the employee report inbox system.")
    
    with gr.Accordion("⚙️ Model & API Settings", open=False):
        gr.Markdown("Configure the AI inference runner for the Auto-Step functionality. Your API Key is not permanently saved.")
        with gr.Row():
            api_key_input = gr.Textbox(label="API Key", type="password", placeholder="sk-...", value=os.environ.get("OPENAI_API_KEY", ""))
            model_input = gr.Textbox(label="Model Name", value=os.environ.get("OPENAI_MODEL", "gpt-4o"))
            base_url_input = gr.Textbox(label="Base URL (Optional)", placeholder="http://localhost:8000/v1", value=os.environ.get("OPENAI_BASE_URL", ""))

    with gr.Row():
        task_dropdown = gr.Dropdown(choices=["1", "2", "3"], label="Select Task ID")
        load_btn = gr.Button("Load Task", variant="primary")
    
    output_area = gr.Textbox(label="Environment State", lines=15)
    
    gr.Markdown("### Take Action")
    with gr.Row():
        action_input = gr.Textbox(label="Action JSON Input", lines=3, placeholder='{"action_type": "read", "item_id": "101", "payload": null}')
    
    with gr.Row():
        auto_step_btn = gr.Button("🤖 Auto-Step with AI", variant="primary")
        step_btn = gr.Button("Manual Step (JSON)", variant="secondary")
    
    load_btn.click(init_env, inputs=[task_dropdown], outputs=[output_area])
    step_btn.click(step_env, inputs=[action_input], outputs=[output_area])
    auto_step_btn.click(
        auto_step_env, 
        inputs=[api_key_input, base_url_input, model_input], 
        outputs=[output_area, action_input]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
