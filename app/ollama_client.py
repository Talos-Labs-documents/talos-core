import json
import re
import ollama

DEFAULT_MODEL = "llama3.2:3b"


FALLBACK_STEPS = [
    "Analyze the request",
    "Break the goal into steps",
    "Prepare for approval-gated execution",
]


def _extract_json_object(text: str) -> str | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


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
- Prioritize:
  - repository structure
  - CLI behavior
  - API flow
  - plan lifecycle (plan → approve → run)
  - output/log/data flow

STRICTLY DO NOT:
- suggest cloning the repo
- suggest installing packages
- suggest creating new files
- suggest writing code
- suggest using git commands
- suggest using shell tools (tree, ls, pip, etc.)
- assume missing features like databases or external systems

Steps must describe WHAT to review, not HOW to run commands.

Keep steps short, concrete, and readable.

No markdown fences.
No explanation outside JSON.
"""

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        print("\n[OLLAMA FULL RESPONSE]")
        print(response)
        print()

        content = response["message"]["content"].strip()

        print("[OLLAMA MESSAGE CONTENT]")
        print(content)
        print()

        json_text = _extract_json_object(content)
        if not json_text:
            print("[OLLAMA ERROR] No JSON object found in model output.")
            return FALLBACK_STEPS

        data = json.loads(json_text)
        steps = data.get("steps", [])

        if isinstance(steps, list):
            cleaned = [str(step).strip() for step in steps if str(step).strip()]
            if cleaned:
                return cleaned

        print("[OLLAMA ERROR] JSON parsed but no valid steps list found.")
        return FALLBACK_STEPS

    except Exception as e:
        print(f"[OLLAMA ERROR] {type(e).__name__}: {e}")
        return FALLBACK_STEPS