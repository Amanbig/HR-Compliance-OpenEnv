"""
src/handlers.py — Gradio event handler functions.

Each handler maps to one UI button/event. Handlers call into
state.py (env), helpers.py (utils), and config.py (constants).
All return tuples that match the Gradio output component list.
"""

import json
from typing import Tuple

import gradio as gr

from env import Action
from src import state
from src.config import MAX_AUTO_STEPS, MODEL, TASK_INFO
from src.helpers import (
    build_system_prompt,
    format_report_details,
    format_reports_md,
    load_task_desc,
    make_openai_client,
    parse_action_json,
    wrap_score_html,
)

# Type alias for the 5-tuple returned by most handlers
_UIOutputs = Tuple[str, str, str, str, str]


# ── Load task ─────────────────────────────────────────────────────────────────


def handle_load_task(task_id: str) -> _UIOutputs:
    """Initialise a fresh env for the selected task."""
    if not task_id:
        return "", "", "", wrap_score_html("-"), "Please select a task first."
    try:
        tid = int(task_id)
        env = state.init_env(tid)
        obs = env._get_obs()
        info = TASK_INFO[tid]
        desc = load_task_desc(tid)
        status = (
            f"**Task {tid}: {info['name']}** ({info['difficulty']}) "
            f"| {len(obs.reports)} reports | Folder: `{obs.current_folder}`"
        )
        return (
            status,
            format_reports_md(obs),
            format_report_details(obs),
            wrap_score_html("-"),
            desc,
        )
    except Exception as exc:
        return "", "", "", wrap_score_html("-"), f"Failed to initialize: {exc}"


# ── Manual step ───────────────────────────────────────────────────────────────


def handle_manual_step(action_str: str) -> _UIOutputs:
    """Execute a user-supplied JSON action."""
    env = state.get_env()
    if not env:
        return "", "", "", gr.update(), "Please load a task first."
    if not action_str or not action_str.strip():
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "Error: Action JSON cannot be empty.",
        )
    try:
        action = Action(**json.loads(action_str))
        obs, reward, done, info = env.step(action)
        score_str = f"{info['score']:.2f}"
        status = " | ".join(
            [
                f"Folder: `{obs.current_folder}`",
                f"{len(obs.reports)} reports",
                *(["**DONE**"] if done else []),
            ]
        )
        log = f"Action: `{action.action_type}({action.item_id})`\nReward: {reward.value:.2f} | {reward.reason}"
        if done:
            log += f"\n\n**Task completed! Final score: {score_str}**"
        return (
            status,
            format_reports_md(obs),
            format_report_details(obs),
            wrap_score_html(score_str),
            log,
        )
    except Exception as exc:
        return gr.update(), gr.update(), gr.update(), gr.update(), f"Error: {exc}"


# ── Single AI step ────────────────────────────────────────────────────────────


def handle_single_ai_step(api_key: str, base_url: str, model_name: str):
    """Ask the LLM for one action and execute it (stateless between clicks)."""
    env = state.get_env()
    task_id = state.get_task_id()
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
            "Set API Key or Base URL in Settings.",
            "",
        )
    try:
        obs = env._get_obs()
        desc = load_task_desc(task_id)
        client = make_openai_client(api_key, base_url)
        resp = client.chat.completions.create(
            model=model_name or MODEL,
            messages=[
                {"role": "system", "content": build_system_prompt(desc)},
                {
                    "role": "user",
                    "content": f"Current observation:\n{obs.model_dump_json()}",
                },
            ],
            temperature=0.2,
            max_tokens=300,
        )
        action_json = resp.choices[0].message.content or ""
        action = Action(**parse_action_json(action_json))
        obs, reward, done, info = env.step(action)
        score_str = f"{info['score']:.2f}"
        status = f"Folder: `{obs.current_folder}` | {len(obs.reports)} reports" + (
            " | **DONE**" if done else ""
        )
        log = f"AI: `{action.action_type}({action.item_id})`\nReward: {reward.value:.2f} | {reward.reason}"
        if done:
            log += f"\n\n**Task completed! Final score: {score_str}**"
        return (
            status,
            format_reports_md(obs),
            format_report_details(obs),
            wrap_score_html(score_str),
            log,
            action_json,
        )
    except Exception as exc:
        return gr.update(), gr.update(), gr.update(), gr.update(), f"Error: {exc}", ""


# ── Full episode ──────────────────────────────────────────────────────────────


def handle_full_episode(api_key: str, base_url: str, model_name: str) -> _UIOutputs:
    """Run a complete multi-step AI episode from a fresh env reset."""
    task_id = state.get_task_id()
    if not task_id:
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
            "Set API Key or Base URL in Settings.",
        )
    try:
        env = state.init_env(task_id)  # fresh reset
        obs = env._get_obs()
        desc = load_task_desc(task_id)
        info_t = TASK_INFO[task_id]
        client = make_openai_client(api_key, base_url)
        model = model_name or MODEL

        messages = [{"role": "system", "content": build_system_prompt(desc)}]
        log_lines = [
            f"### Task {task_id}: {info_t['name']} ({info_t['difficulty']})",
            f"*{desc.strip()}*\n",
            "| Step | Action | Reward | Feedback |",
            "|:----:|:-------|:------:|:---------|",
        ]
        final_score = 0.0
        final_step = MAX_AUTO_STEPS
        done = False

        for step in range(1, MAX_AUTO_STEPS + 1):
            messages.append(
                {
                    "role": "user",
                    "content": f"Step {step}/{MAX_AUTO_STEPS}. Current observation:\n{obs.model_dump_json(indent=2)}",
                }
            )
            # LLM call
            try:
                resp = client.chat.completions.create(
                    model=model, messages=messages, temperature=0.2, max_tokens=300
                )
                response_text = resp.choices[0].message.content or ""
            except Exception as exc:
                log_lines.append(f"| {step} | API Error | — | {exc} |")
                break

            messages.append({"role": "assistant", "content": response_text})

            # Parse action
            try:
                action = Action(**parse_action_json(response_text))
            except Exception:
                log_lines.append(f"| {step} | Parse Error | — | Bad JSON |")
                messages.append(
                    {
                        "role": "user",
                        "content": "Invalid JSON. Output ONLY a valid JSON action object.",
                    }
                )
                continue

            # Step environment
            obs, reward, done, info = env.step(action)
            final_score = info.get("score", 0.0)
            payload_str = f", '{action.payload}'" if action.payload else ""
            reason_short = reward.reason[:60] + ("…" if len(reward.reason) > 60 else "")
            log_lines.append(
                f"| {step} | `{action.action_type}({action.item_id}{payload_str})` "
                f"| {reward.value:.2f} | {reason_short} |"
            )
            if done:
                final_step = step
                break

            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Reward: {reward.value:.2f} | Progress: {reward.partial_progress:.2f} "
                        f"| Penalties: {reward.penalties:.2f} | {reward.reason}"
                    ),
                }
            )

        outcome = "Completed" if done else "Max steps reached"
        log_lines.append(
            f"\n**{outcome} — Steps: {final_step} | Final score: {final_score:.2f}**"
        )

        final_obs = env._get_obs()
        score_str = f"{final_score:.2f}"
        status = (
            f"**Task {task_id}: {info_t['name']}** | Score: {score_str} | Steps: {final_step}"
            + (" ✓ PASSED" if final_score >= 1.0 else "")
        )
        return (
            status,
            format_reports_md(final_obs),
            format_report_details(final_obs),
            wrap_score_html(score_str),
            "\n".join(log_lines),
        )
    except Exception as exc:
        return gr.update(), gr.update(), gr.update(), gr.update(), f"Error: {exc}"
