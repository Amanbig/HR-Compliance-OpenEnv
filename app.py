import gradio as gr
from env import HRComplianceEnv, Action
import yaml
import json

env = None

def init_env(task_id):
    global env
    try:
        task_id_int = int(task_id)
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
    
    try:
        action_dict = json.loads(action_str)
        action = Action(**action_dict)
        obs, reward, done, info = env.step(action)
        return f"Observation:\n{obs.model_dump_json(indent=2)}\n\nReward:\n{reward.model_dump_json(indent=2)}\n\nDone: {done}\n\nInfo: {info}"
    except Exception as e:
        return f"Error executing step: {str(e)}"

with gr.Blocks(title="OpenEnv - HR Compliance") as demo:
    gr.Markdown("# HR Compliance Review Environment")
    gr.Markdown("Simulate actions as an HR compliance officer interacting with the employee report inbox system.")
    
    with gr.Row():
        task_dropdown = gr.Dropdown(choices=["1", "2", "3"], label="Select Task ID")
        load_btn = gr.Button("Load Task", variant="primary")
    
    output_area = gr.Textbox(label="Environment State", lines=15)
    
    load_btn.click(init_env, inputs=[task_dropdown], outputs=[output_area])
    
    gr.Markdown("### Take Action")
    gr.Markdown("""Provide JSON matching the Action Pydantic model. 
Example JSON for `read` Action: `{"action_type": "read", "item_id": "101", "payload": null}`
""")
    with gr.Row():
        action_input = gr.Textbox(label="Action JSON Input", lines=3)
        step_btn = gr.Button("Step Environment")
    
    step_btn.click(step_env, inputs=[action_input], outputs=[output_area])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
