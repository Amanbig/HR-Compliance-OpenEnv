"""
Inference Script for OpenEnv HR Compliance Environment
=======================================================
MANDATORY environment variables:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

Usage:
    export API_BASE_URL="https://router.huggingface.co/v1"
    export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
    export HF_TOKEN="hf_..."
    python inference.py
"""

import os
import json
import textwrap
from typing import List

from openai import OpenAI

from env import HRComplianceEnv, Action
import yaml

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
MAX_STEPS = 15
TEMPERATURE = 0.2
MAX_TOKENS = 300

SYSTEM_PROMPT_TEMPLATE = textwrap.dedent("""\
You are an AI HR Compliance Officer working in an employee report inbox system.
Your current task: {task_desc}

You interact with the environment by outputting a single JSON action matching this schema:
{{
  "action_type": "<type>",
  "item_id": "<report id string>",
  "payload": "<string or null>"
}}

Action types and payloads:
- "read"     → payload: null. Mark a report as read.
- "reply"    → payload: reply text. Send a reply to the report.
- "move"     → payload: folder name (e.g. "IT_Support", "Confidential").
- "delete"   → payload: null. Move to trash.
- "tag"      → payload: tag string (e.g. "safety_hazard", "investigation_required").
- "escalate" → payload: team name (e.g. "Legal", "Security", "HR_Investigation", "Management").
- "flag"     → payload: "urgent" | "high" | "normal". Set report priority.
- "assign"   → payload: team or person name (e.g. "HR_Investigation").
- "close"    → payload: null. Resolve and close a report.

Strategy tips:
- First read reports to understand content, then act. One action per step.
- Task 1: Move IT support reports to "IT_Support". Leave others alone.
- Task 2: Tag genuine physical hazards "safety_hazard" + reply. No false positives.
- Task 3: Move embezzlement/whistleblower report to "Confidential", tag "investigation_required". Ignore gossip.
- Task 4: Escalate genuine legal threats (retained counsel, lawsuits) to "Legal". Do NOT escalate venting.
- Task 5: Find 3 reports from the same victim (harassment pattern). Flag all as "urgent" + assign to "HR_Investigation".

Output ONLY valid JSON. No explanation, no markdown, just the JSON object.""")


def load_task_description(task_id: int) -> str:
    with open("openenv.yaml", "r") as f:
        meta = yaml.safe_load(f)
    return next(
        (t["description"] for t in meta["tasks"] if t["id"] == task_id),
        "Unknown task",
    )


def parse_action(response_text: str) -> dict:
    """Extract a JSON action dict from the model response."""
    text = response_text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def run_task(task_id: int, client: OpenAI) -> float:
    """Run one task end-to-end and return the final score."""
    env = HRComplianceEnv(task_id)
    obs = env.reset()

    task_desc = load_task_description(task_id)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(task_desc=task_desc)

    messages: List[dict] = [{"role": "system", "content": system_prompt}]

    print(f"\n{'=' * 60}")
    print(f"Task {task_id}: {task_desc}")
    print(f"{'=' * 60}")

    final_score = 0.0

    for step in range(1, MAX_STEPS + 1):
        obs_text = obs.model_dump_json(indent=2)
        messages.append(
            {
                "role": "user",
                "content": f"Step {step}/{MAX_STEPS}. Current observation:\n{obs_text}",
            }
        )

        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            response_text = completion.choices[0].message.content or ""
        except Exception as exc:
            print(f"  Step {step}: API error — {exc}")
            messages.append(
                {
                    "role": "assistant",
                    "content": '{"action_type": "read", "item_id": "none"}',
                }
            )
            break

        messages.append({"role": "assistant", "content": response_text})

        try:
            action_dict = parse_action(response_text)
            action = Action(**action_dict)
        except Exception as exc:
            print(f"  Step {step}: Parse error — {exc}")
            print(f"  Raw response: {response_text[:200]}")
            # Ask model to retry
            messages.append(
                {
                    "role": "user",
                    "content": "Your last response was not valid JSON. Please output ONLY a valid JSON action object.",
                }
            )
            continue

        obs, reward, done, info = env.step(action)
        final_score = info.get("score", 0.0)

        print(
            f"  Step {step}: {action.action_type}({action.item_id}"
            f"{', ' + repr(action.payload) if action.payload else ''}) "
            f"→ reward={reward.value:.2f} progress={reward.partial_progress:.2f} "
            f"penalty={reward.penalties:.2f} | {reward.reason}"
        )

        if done:
            print(f"  Task completed at step {step}. Score: {final_score:.2f}")
            break

        # Feed reward info back to model
        messages.append(
            {
                "role": "user",
                "content": f"Action executed. Reward: {reward.value:.2f}, "
                f"Progress: {reward.partial_progress:.2f}, "
                f"Penalties: {reward.penalties:.2f}. "
                f"Feedback: {reward.reason}",
            }
        )
    else:
        print(f"  Reached max steps ({MAX_STEPS}). Final score: {final_score:.2f}")

    return final_score


def main() -> None:
    if not API_KEY:
        print("ERROR: HF_TOKEN (or API_KEY) environment variable not set.")
        print("Please set it: export HF_TOKEN='hf_...'")
        return

    print(f"API Base URL: {API_BASE_URL}")
    print(f"Model: {MODEL_NAME}")

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = {}
    for task_id in [1, 2, 3, 4, 5]:
        score = run_task(task_id, client)
        scores[task_id] = score

    print(f"\n{'=' * 60}")
    print("BASELINE RESULTS")
    print(f"{'=' * 60}")
    for tid, sc in scores.items():
        print(f"  Task {tid}: {sc:.2f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  Average:  {avg:.2f}")


if __name__ == "__main__":
    main()
