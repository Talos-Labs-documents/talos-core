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


def generate_plan_steps(goal: str, model: str = DEFAULT_MODEL):
    prompt = f"""
You are generating execution steps for TALOS, a local orchestration system.

User goal:
{goal}

CRITICAL CONTEXT:
- This is an EXISTING local Python repository
- DO NOT suggest cloning, installing dependencies, creating files, or setting up environments
- The system already exists and should be INSPECTED, EXPLAINED, and ANALYZED
- TALOS uses approval-gated execution and writes outputs, plans, and logs to disk

AVAILABLE EXECUTION CAPABILITIES:
- review repository structure
- analyze CLI flow in app/main.py
- analyze API routes and endpoint behavior in app/api.py
- analyze plan lifecycle in app/api.py
- analyze output/log/data flow in data/
- inspect docs/ folder
- summarize specific files such as app/main.py, app/api.py, app/ollama_client.py, README.md

YOUR JOB:
Break the user's goal into 3 to 6 concrete analysis steps that TALOS can execute.

IMPORTANT:
- Steps must be SPECIFIC and ACTIONABLE
- Steps should align with the execution capabilities above
- Prefer direct references to real repo locations like:
  - app/main.py
  - app/api.py
  - app/ollama_client.py
  - data/
  - docs/
- Use wording that naturally maps to existing executors

STRICTLY DO NOT:
- write generic steps like:
  - "Analyze the request"
  - "Break the goal into steps"
  - "Prepare for approval-gated execution"
- suggest cloning the repo
- suggest installing packages
- suggest creating files
- suggest unrelated setup work
- assume databases, external services, or missing infrastructure unless explicitly asked

GOOD STEP EXAMPLES:
- "Review API routes defined in app/api.py"
- "Analyze CLI command flow in app/main.py"
- "Explain the plan lifecycle implemented in app/api.py"
- "Describe how outputs, plans, and logs are written under data/"
- "Inspect the docs folder and summarize available documentation"
- "Summarize app/main.py and explain why it matters to contributors"

Return ONLY valid JSON in this exact format:
{{
  "steps": [
    "Step 1",
    "Step 2",
    "Step 3"
  ]
}}
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
            cleaned = [str(step).strip() for step in steps if str(step).strip()]
            if 3 <= len(cleaned) <= 6:
                return cleaned
            if cleaned:
                return cleaned[:6]

    except Exception as e:
        print(f"[OLLAMA PLAN ERROR] {type(e).__name__}: {e}")

    return FALLBACK_STEPS


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
        print(f"[OLLAMA REPO SUMMARY ERROR] {type(e).__name__}: {e}")

    return ""


def generate_file_explanation(file_path: str, content: str, model: str = DEFAULT_MODEL) -> str:
    prompt = f"""
You are explaining a file inside an early-alpha local orchestration system called TALOS.

Your job:
- Explain what this file appears to do
- Stay grounded ONLY in the provided file content
- Do NOT invent functionality that is not visible in the file
- Keep the explanation concise and contributor-friendly

Return plain text only.

Structure:
1. One short overview paragraph
2. A short bullet list of the most important responsibilities in this file
3. One short sentence telling a contributor why this file matters

File path:
{file_path}

File content:
{content}
"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        content_out = response["message"]["content"].strip()
        if content_out:
            return content_out

    except Exception as e:
        print(f"[OLLAMA FILE SUMMARY ERROR] {type(e).__name__}: {e}")

    return ""


def generate_api_explanation(context: str, model: str = DEFAULT_MODEL) -> str:
    prompt = f"""
You are explaining the API flow of an early-alpha local orchestration system called TALOS.

Your job:
- Explain the API clearly for a new contributor
- Stay grounded ONLY in the provided context
- Do NOT invent routes, request types, or systems not present

Return plain text only.

Structure:
1. One short overview paragraph
2. A short bullet list of the most important routes or responsibilities
3. One short sentence explaining why this API layer matters

API context:
{context}
"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        content_out = response["message"]["content"].strip()
        if content_out:
            return content_out

    except Exception as e:
        print(f"[OLLAMA API SUMMARY ERROR] {type(e).__name__}: {e}")

    return ""


def generate_plan_lifecycle_explanation(context: str, model: str = DEFAULT_MODEL) -> str:
    prompt = f"""
You are explaining the plan lifecycle of an early-alpha local orchestration system called TALOS.

Your job:
- Explain how plans move through the system
- Stay grounded ONLY in the provided context
- Do NOT invent lifecycle stages that are not present

Return plain text only.

Structure:
1. One short overview paragraph
2. A short bullet list of the most important lifecycle stages
3. One short sentence explaining why this lifecycle matters

Plan lifecycle context:
{context}
"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        content_out = response["message"]["content"].strip()
        if content_out:
            return content_out

    except Exception as e:
        print(f"[OLLAMA PLAN LIFECYCLE ERROR] {type(e).__name__}: {e}")

    return ""


def generate_output_flow_explanation(context: str, model: str = DEFAULT_MODEL) -> str:
    prompt = f"""
You are explaining the output and storage flow of an early-alpha local orchestration system called TALOS.

Your job:
- Explain how data is written and stored
- Stay grounded ONLY in the provided context
- Do NOT invent storage layers or systems not present

Return plain text only.

Structure:
1. One short overview paragraph
2. A short bullet list of the most important storage directories or artifacts
3. One short sentence explaining why this storage flow matters

Output/storage context:
{context}
"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )

        content_out = response["message"]["content"].strip()
        if content_out:
            return content_out

    except Exception as e:
        print(f"[OLLAMA OUTPUT FLOW ERROR] {type(e).__name__}: {e}")

    return ""