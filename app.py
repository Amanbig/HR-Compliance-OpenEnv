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

API_KEY = (
    os.environ.get("HF_TOKEN")
    or os.environ.get("API_KEY")
    or os.environ.get("OPENAI_API_KEY", "")
)
API_BASE = os.environ.get("API_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "")
MODEL = os.environ.get("MODEL_NAME") or os.environ.get(
    "OPENAI_MODEL", "meta-llama/Llama-3.3-70B-Instruct"
)

MAX_AUTO_STEPS = 15

TASK_INFO = {
    1: {"name": "IT Ticket Routing", "difficulty": "Easy", "color": "#22c55e"},
    2: {
        "name": "Workplace Safety Violations",
        "difficulty": "Medium",
        "color": "#f59e0b",
    },
    3: {"name": "Whistleblower Escalation", "difficulty": "Hard", "color": "#ef4444"},
}

CSS = """
.main-header {
    text-align: center;
    padding: 1.5rem 0 0.5rem 0;
}
.main-header h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}
.main-header p {
    color: #6b7280;
    font-size: 0.95rem;
}
.task-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    cursor: pointer;
    transition: all 0.2s;
    background: #fafafa;
    min-height: 90px;
}
.task-card:hover {
    border-color: #6366f1;
    box-shadow: 0 2px 8px rgba(99,102,241,0.15);
}
.task-card h3 {
    margin: 0 0 0.25rem 0;
    font-size: 1rem;
}
.task-card .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
}
.score-display {
    font-size: 2.5rem;
    font-weight: 800;
    text-align: center;
    padding: 0.5rem;
    font-family: monospace;
}
.score-label {
    text-align: center;
    color: #6b7280;
    font-size: 0.85rem;
}
.step-log {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
}
.status-bar {
    display: flex;
    gap: 1rem;
    align-items: center;
    padding: 0.75rem 1rem;
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
    font-size: 0.9rem;
}
footer {
    display: none !important;
}
"""


def load_task_desc(task_id_int):
    with open("openenv.yaml", "r") as f:
        meta = yaml.safe_load(f)
    return next(
        (t["description"] for t in meta["tasks"] if t["id"] == task_id_int),
        "Unknown task",
    )


def build_system_prompt(task_desc):
    return f"""You are an AI HR Compliance Officer. Your task: {task_desc}
You can take actions by outputting JSON matching this schema:
{{"action_type": one of ["read", "reply", "move", "delete", "tag"], "item_id": "<report id>", "payload": "<optional string>"}}

Available actions:
- read: marks report as read. payload is null.
- reply: payload = your reply text.
- move: payload = destination folder name (e.g. "IT_Support", "Confidential").
- delete: moves to trash. payload is null.
- tag: payload = the tag string (e.g. "safety_hazard", "investigation_required").

Strategy:
- First read reports to understand content, then act.
- One action per response.

Output ONLY valid JSON. No explanation."""


def parse_action_json(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def format_reports_md(obs):
    """Render reports as a readable markdown table."""
    reports = obs.reports
    if not reports:
        return "*No reports in this folder.*"

    lines = [
        "| ID | Sender | Subject | Tags | Read | Replied |",
        "|:---|:-------|:--------|:-----|:----:|:-------:|",
    ]
    for r in reports:
        tags = ", ".join(r.tags) if r.tags else "-"
        read_icon = "Yes" if r.read else "-"
        replied_icon = "Yes" if r.replied else "-"
        lines.append(
            f"| `{r.id}` | {r.sender} | **{r.subject}** | {tags} | {read_icon} | {replied_icon} |"
        )
    return "\n".join(lines)


def format_report_details(obs):
    """Show full body of each report."""
    if not obs.reports:
        return ""
    parts = []
    for r in obs.reports:
        parts.append(f"**[{r.id}] {r.subject}**\nFrom: {r.sender}\n> {r.body}\n")
    return "\n---\n".join(parts)


def init_env(task_id):
    global env, current_task_id
    if not task_id:
        return "", "", "", "Please select a task first."
    try:
        task_id_int = int(task_id)
        current_task_id = task_id_int
        env = HRComplianceEnv(task_id_int)
        obs = env.reset()

        info = TASK_INFO[task_id_int]
        task_desc = load_task_desc(task_id_int)

        status = f"**Task {task_id_int}: {info['name']}** ({info['difficulty']}) | {len(obs.reports)} reports in inbox | Folder: `{obs.current_folder}`"
        reports_md = format_reports_md(obs)
        details_md = format_report_details(obs)

        return status, reports_md, details_md, f"Environment ready. {task_desc}"
    except Exception as e:
        return "", "", "", f"Failed to initialize: {e}"


def step_env(action_str):
    global env
    if not env:
        return "", "", "", "-", "Please load a task first."
    if not action_str or not action_str.strip():
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "Error: Action JSON cannot be empty.",
        )
    try:
        action_dict = json.loads(action_str)
        action = Action(**action_dict)
        obs, reward, done, info = env.step(action)

        reports_md = format_reports_md(obs)
        details_md = format_report_details(obs)
        score_str = f"{info['score']:.2f}"

        status_parts = [
            f"Folder: `{obs.current_folder}`",
            f"{len(obs.reports)} reports",
        ]
        if done:
            status_parts.append("**DONE**")
        status = " | ".join(status_parts)

        log = f"Action: `{action.action_type}({action.item_id})`\nReward: {reward.value:.2f} | {reward.reason}"
        if done:
            log += f"\n\n**Task completed! Final score: {score_str}**"

        return status, reports_md, details_md, score_str, log
    except Exception as e:
        return gr.update(), gr.update(), gr.update(), gr.update(), f"Error: {e}"


def auto_step_env(api_key, base_url, model_name):
    global env, current_task_id
    if not env:
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "Please load a task first.",
            "",
        )
    if not api_key and not base_url:
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "Error: Set API Key or Base URL in Settings.",
            "",
        )

    try:
        task_desc = load_task_desc(current_task_id)
        system_prompt = build_system_prompt(task_desc)
        obs = env._get_obs()

        client = OpenAI(
            api_key=api_key if api_key else "dummy_key",
            base_url=base_url if base_url else None,
        )
        resp = client.chat.completions.create(
            model=model_name if model_name else "meta-llama/Llama-3.3-70B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Current observation:\n{obs.model_dump_json()}",
                },
            ],
            temperature=0.2,
            max_tokens=300,
        )
        action_json = resp.choices[0].message.content

        action_dict = json.loads(action_json)
        action = Action(**action_dict)
        obs, reward, done, info = env.step(action)

        reports_md = format_reports_md(obs)
        details_md = format_report_details(obs)
        score_str = f"{info['score']:.2f}"
        status = f"Folder: `{obs.current_folder}` | {len(obs.reports)} reports" + (
            " | **DONE**" if done else ""
        )

        log = f"AI chose: `{action.action_type}({action.item_id})`\nReward: {reward.value:.2f} | {reward.reason}"
        if done:
            log += f"\n\n**Task completed! Final score: {score_str}**"

        return status, reports_md, details_md, score_str, log, action_json
    except Exception as e:
        return gr.update(), gr.update(), gr.update(), gr.update(), f"Error: {e}", ""


def run_full_episode(api_key, base_url, model_name):
    global env, current_task_id
    if not env and not current_task_id:
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "Please load a task first.",
        )
    if not api_key and not base_url:
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "Error: Set API Key or Base URL in Settings.",
        )

    try:
        env_local = HRComplianceEnv(current_task_id)
        obs = env_local.reset()
        env = env_local

        task_desc = load_task_desc(current_task_id)
        system_prompt = build_system_prompt(task_desc)
        info_t = TASK_INFO[current_task_id]

        client = OpenAI(
            api_key=api_key if api_key else "dummy_key",
            base_url=base_url if base_url else None,
        )
        model = model_name if model_name else "meta-llama/Llama-3.3-70B-Instruct"

        messages = [{"role": "system", "content": system_prompt}]
        log_lines = [
            f"### Task {current_task_id}: {info_t['name']} ({info_t['difficulty']})",
            f"*{task_desc.strip()}*\n",
            "| Step | Action | Reward | Feedback |",
            "|:----:|:-------|:------:|:---------|",
        ]

        final_score = 0.0
        final_step = MAX_AUTO_STEPS

        for step in range(1, MAX_AUTO_STEPS + 1):
            obs_text = obs.model_dump_json(indent=2)
            messages.append(
                {
                    "role": "user",
                    "content": f"Step {step}/{MAX_AUTO_STEPS}. Current observation:\n{obs_text}",
                }
            )

            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=300,
                )
                response_text = resp.choices[0].message.content or ""
            except Exception as exc:
                log_lines.append(f"| {step} | API Error | - | {exc} |")
                break

            messages.append({"role": "assistant", "content": response_text})

            try:
                action_dict = parse_action_json(response_text)
                action = Action(**action_dict)
            except Exception:
                log_lines.append(f"| {step} | Parse Error | - | Bad JSON from model |")
                messages.append(
                    {
                        "role": "user",
                        "content": "Invalid JSON. Output ONLY a valid JSON action object.",
                    }
                )
                continue

            obs, reward, done, info = env.step(action)
            final_score = info.get("score", 0.0)

            payload_str = f", '{action.payload}'" if action.payload else ""
            action_str = f"`{action.action_type}({action.item_id}{payload_str})`"
            reason_short = reward.reason[:60] + (
                "..." if len(reward.reason) > 60 else ""
            )
            log_lines.append(
                f"| {step} | {action_str} | {reward.value:.2f} | {reason_short} |"
            )

            if done:
                final_step = step
                break

            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Action executed. Reward: {reward.value:.2f}, "
                        f"Progress: {reward.partial_progress:.2f}, "
                        f"Penalties: {reward.penalties:.2f}. "
                        f"Feedback: {reward.reason}"
                    ),
                }
            )

        if done:
            log_lines.append(
                f"\n**Completed in {final_step} steps. Final score: {final_score:.2f}**"
            )
        else:
            log_lines.append(
                f"\n**Reached max steps ({MAX_AUTO_STEPS}). Score: {final_score:.2f}**"
            )

        final_obs = env._get_obs()
        reports_md = format_reports_md(final_obs)
        details_md = format_report_details(final_obs)
        score_str = f"{final_score:.2f}"
        status = (
            f"**Task {current_task_id}: {info_t['name']}** | Score: {score_str} | Steps: {final_step}"
            + (" | PASSED" if final_score >= 1.0 else "")
        )

        return status, reports_md, details_md, score_str, "\n".join(log_lines)

    except Exception as e:
        return gr.update(), gr.update(), gr.update(), gr.update(), f"Error: {e}"


with gr.Blocks(title="OpenEnv - HR Compliance Review") as demo:
    # Header
    gr.HTML("""
    <div class="main-header">
        <h1>HR Compliance Review</h1>
        <p>OpenEnv environment &mdash; Triage employee reports, route tickets, identify safety hazards, and escalate whistleblower complaints.</p>
    </div>
    """)

    # Settings
    with gr.Accordion("Model & API Settings", open=False):
        with gr.Row():
            api_key_input = gr.Textbox(
                label="API Key (HF_TOKEN)",
                type="password",
                placeholder="hf_...",
                value=API_KEY,
                scale=2,
            )
            model_input = gr.Textbox(label="Model", value=MODEL, scale=2)
            base_url_input = gr.Textbox(
                label="Base URL",
                placeholder="https://router.huggingface.co/v1",
                value=API_BASE,
                scale=2,
            )

    # Task Selection
    gr.Markdown("### Select a Task")
    with gr.Row(equal_height=True):
        task_dropdown = gr.Radio(
            choices=[
                ("Task 1: IT Ticket Routing (Easy)", "1"),
                ("Task 2: Safety Violations (Medium)", "2"),
                ("Task 3: Whistleblower Escalation (Hard)", "3"),
            ],
            label="",
            value="1",
        )
        load_btn = gr.Button("Load Task", variant="primary", scale=0, min_width=140)

    # Status Bar
    status_bar = gr.Markdown("*Select a task and click Load Task to begin.*")

    # Main Content - two columns
    with gr.Row():
        # Left: Reports
        with gr.Column(scale=3):
            gr.Markdown("### Inbox")
            reports_table = gr.Markdown("*No reports loaded.*")

            with gr.Accordion("Report Details (full text)", open=False):
                report_details = gr.Markdown("*Load a task to see reports.*")

        # Right: Score + Controls
        with gr.Column(scale=1, min_width=250):
            gr.Markdown("### Score")
            score_display = gr.Markdown(
                "<div class='score-display'>-</div><div class='score-label'>current score</div>"
            )

            gr.Markdown("---")
            gr.Markdown("### AI Controls")
            full_episode_btn = gr.Button(
                "Run Full Episode", variant="primary", size="lg"
            )
            auto_step_btn = gr.Button("Single AI Step", variant="secondary")

            gr.Markdown("---")
            gr.Markdown("### Manual Control")
            action_input = gr.Textbox(
                label="Action JSON",
                lines=2,
                placeholder='{"action_type":"read","item_id":"IT-101"}',
            )
            step_btn = gr.Button("Execute Step", variant="secondary")

    # Episode Log
    gr.Markdown("### Episode Log")
    log_output = gr.Markdown("*Run an episode to see the step-by-step log.*")

    # --- Event wiring ---

    def wrap_score_html(score_str):
        return f"<div class='score-display'>{score_str}</div><div class='score-label'>current score</div>"

    def on_load(task_id):
        status, reports, details, msg = init_env(task_id)
        return status, reports, details, wrap_score_html("-"), msg

    def on_step(action_str):
        status, reports, details, score_str, log = step_env(action_str)
        if isinstance(score_str, str) and score_str != "-":
            return status, reports, details, wrap_score_html(score_str), log
        return status, reports, details, gr.update(), log

    def on_auto_step(api_key, base_url, model_name):
        result = auto_step_env(api_key, base_url, model_name)
        status, reports, details, score_str, log, action_json = result
        if isinstance(score_str, str):
            return (
                status,
                reports,
                details,
                wrap_score_html(score_str),
                log,
                action_json,
            )
        return status, reports, details, gr.update(), log, action_json

    def on_full_episode(api_key, base_url, model_name):
        result = run_full_episode(api_key, base_url, model_name)
        status, reports, details, score_str, log = result
        if isinstance(score_str, str):
            return status, reports, details, wrap_score_html(score_str), log
        return status, reports, details, gr.update(), log

    load_btn.click(
        on_load,
        inputs=[task_dropdown],
        outputs=[status_bar, reports_table, report_details, score_display, log_output],
    )
    step_btn.click(
        on_step,
        inputs=[action_input],
        outputs=[status_bar, reports_table, report_details, score_display, log_output],
    )
    auto_step_btn.click(
        on_auto_step,
        inputs=[api_key_input, base_url_input, model_input],
        outputs=[
            status_bar,
            reports_table,
            report_details,
            score_display,
            log_output,
            action_input,
        ],
    )
    full_episode_btn.click(
        on_full_episode,
        inputs=[api_key_input, base_url_input, model_input],
        outputs=[status_bar, reports_table, report_details, score_display, log_output],
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=CSS,
        theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
    )
