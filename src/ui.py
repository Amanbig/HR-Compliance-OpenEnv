"""
src/ui.py — Gradio Blocks UI layout and event wiring.

Imports handlers from src/handlers.py and constants from src/config.py.
The resulting `demo` object is mounted onto FastAPI in app.py.
"""

import gradio as gr

from src.config import API_BASE, API_KEY, MODEL
from src.handlers import (
    handle_full_episode,
    handle_load_task,
    handle_manual_step,
    handle_single_ai_step,
)
from src.helpers import wrap_score_html

# ── Gradio Blocks ─────────────────────────────────────────────────────────────

with gr.Blocks(title="OpenEnv — HR Compliance Review") as demo:
    # Header
    gr.HTML("""
    <div class="main-header">
        <h1>HR Compliance Review</h1>
        <p>OpenEnv environment — triage reports, route IT tickets, identify hazards,
           escalate legal threats, and detect harassment patterns.</p>
    </div>
    """)

    # Settings
    with gr.Accordion("Model & API Settings", open=False):
        with gr.Row():
            ui_api_key = gr.Textbox(
                label="API Key (HF_TOKEN)",
                type="password",
                placeholder="hf_...",
                value=API_KEY,
                scale=2,
            )
            ui_model = gr.Textbox(label="Model", value=MODEL, scale=2)
            ui_base_url = gr.Textbox(
                label="Base URL",
                placeholder="https://router.huggingface.co/v1",
                value=API_BASE,
                scale=2,
            )

    # Task selection
    gr.Markdown("### Select a Task")
    with gr.Row(equal_height=True):
        ui_task = gr.Radio(
            choices=[
                ("1 — IT Ticket Routing          (Easy)", "1"),
                ("2 — Safety Violations          (Medium)", "2"),
                ("3 — Whistleblower Escalation   (Hard)", "3"),
                ("4 — Legal Threat Routing       (Medium-Hard)", "4"),
                ("5 — Harassment Pattern         (Hard)", "5"),
            ],
            label="",
            value="1",
        )
        ui_load_btn = gr.Button("Load Task", variant="primary", scale=0, min_width=140)

    ui_status = gr.Markdown("*Select a task and click Load Task to begin.*")

    # Main layout — inbox (left) + controls (right)
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("### Inbox")
            ui_reports_table = gr.Markdown("*No reports loaded.*")
            with gr.Accordion("Full report text", open=False):
                ui_report_details = gr.Markdown("*Load a task to see reports.*")

        with gr.Column(scale=1, min_width=260):
            gr.Markdown("### Score")
            ui_score = gr.Markdown(wrap_score_html("-"))

            gr.Markdown("---\n### AI Controls")
            ui_full_btn = gr.Button("Run Full Episode", variant="primary", size="lg")
            ui_step_btn = gr.Button("Single AI Step", variant="secondary")

            gr.Markdown("---\n### Manual Control")
            ui_action_input = gr.Textbox(
                label="Action JSON",
                lines=2,
                placeholder='{"action_type":"read","item_id":"IT-101","payload":null}',
            )
            ui_manual_btn = gr.Button("Execute Step", variant="secondary")

    gr.Markdown("### Episode Log")
    ui_log = gr.Markdown("*Run an episode to see the step-by-step log.*")

    # ── Event wiring ──────────────────────────────────────────────────────────
    _OUTPUTS = [ui_status, ui_reports_table, ui_report_details, ui_score, ui_log]

    ui_load_btn.click(handle_load_task, inputs=[ui_task], outputs=_OUTPUTS)
    ui_manual_btn.click(handle_manual_step, inputs=[ui_action_input], outputs=_OUTPUTS)
    ui_step_btn.click(
        handle_single_ai_step,
        inputs=[ui_api_key, ui_base_url, ui_model],
        outputs=[*_OUTPUTS, ui_action_input],
    )
    ui_full_btn.click(
        handle_full_episode,
        inputs=[ui_api_key, ui_base_url, ui_model],
        outputs=_OUTPUTS,
    )
