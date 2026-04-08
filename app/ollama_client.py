import json
import re
import ollama

DEFAULT_MODEL = "llama3.2:3b"

FALLBACK_STEPS = [
    "Analyze the request",
    "Break the goal into steps",
    "Prepare for approval-gated execution",
]


def _extract_json_object(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None


# 🧠 PLANNER
def generate_plan_steps(goal: str, model: str = DEFAULT_MODEL):
    prompt = f"""
You are planning a safe, approval-gated execution plan for a local orchestration system called TALOS.

User goal:
{goal}

Context:
- This is an existing local Python repository
- The system is already cloned and running locally
- The project contains folders like app/, data/, docs/, scripts/
- TALOS is an early alpha system focused on:
  - CLI interaction
  - API endpoints
  - plan → approval → execution flow
  - writing outputs to disk

Your job is to generate steps to UNDERSTAND and EXPLAIN the system, not to modify or rebuild it.

Return only valid JSON in this format:
{{
  "steps": [
    "Step 1",
    "Step 2",
    "Step 3"
  ]
}}

Rules:
- Return 3 to 6 steps
- Focus on understanding, reviewing, and explaining the system
- Do NOT suggest commands, setup steps, or file creation
- No markdown fences
- No explanation outside JSON
"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response["message"]["content"].strip()

        json_text = _extract_json_object(content)
        if not json_text:
            return FALLBACK_STEPS

        data = json.loads(json_text)
        steps = data.get("steps", [])

        if isinstance(steps, list) and steps:
            return steps

    except Exception as e:
        print(f"[OLLAMA PLAN ERROR] {type(e).__name__}: {e}")

    return FALLBACK_STEPS


# 🧠 EXECUTION SUMMARY (LLM-powered)
def generate_repo_explanation(context: str, model: str = DEFAULT_MODEL) -> str:
    prompt = f"""
You are writing a contributor-facing repository summary for an early-alpha local orchestration system called TALOS.

Your job:
- Explain the repository clearly for a new contributor
- Stay grounded ONLY in the provided context
- Do NOT invent features, files, or systems not present

Return plain text only.

Structure:
1. Short overview paragraph
2. Bullet list of key components
3. Explanation of execution flow
4. Where a contributor should start

Repository context:
{context}
"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response["message"]["content"].strip()

        if content:
            return content

    except Exception as e:
        print(f"[OLLAMA SUMMARY ERROR] {type(e).__name__}: {e}")

    return ""