from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests


OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"


class OllamaError(Exception):
    """Raised when an Ollama request or response fails."""


def _post_generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
) -> str:
    """
    Send a non-streaming generate request to Ollama and return the raw text response.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    if system:
        payload["system"] = system

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise OllamaError(f"Failed to call Ollama generate API: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise OllamaError(f"Ollama returned a non-JSON HTTP response: {response.text}") from e

    text = data.get("response", "")
    if not isinstance(text, str):
        raise OllamaError(f"Ollama response missing text field: {data}")

    return text.strip()


def _extract_first_json_object(raw: str) -> Dict[str, Any]:
    """
    Extract and parse the first balanced JSON object found in a string.
    Useful when the model wraps valid JSON with extra chatter.
    """
    start = raw.find("{")
    if start == -1:
        raise OllamaError(f"No JSON object found in model output.\nRaw output:\n{raw}")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(raw)):
        char = raw[i]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = raw[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError as e:
                    raise OllamaError(
                        f"Found a JSON-like block but could not parse it.\nCandidate:\n{candidate}"
                    ) from e

                if not isinstance(parsed, dict):
                    raise OllamaError(
                        f"Expected a JSON object but got: {type(parsed).__name__}\nCandidate:\n{candidate}"
                    )

                return parsed

    raise OllamaError(f"Could not find a complete balanced JSON object.\nRaw output:\n{raw}")


def ask_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
) -> str:
    """
    Return raw text from the model.
    """
    return _post_generate(prompt=prompt, model=model, system=system)


def ask_llm_json(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return JSON from the model.
    First tries direct parsing, then falls back to extracting the first JSON object.
    """
    raw = _post_generate(prompt=prompt, model=model, system=system)

    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise OllamaError(
                f"Expected a JSON object but got: {type(parsed).__name__}\nRaw output:\n{raw}"
            )
        return parsed
    except json.JSONDecodeError:
        return _extract_first_json_object(raw)


def generate_plan_steps(goal: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Ask the model to turn a goal into a small execution plan.
    Expected return shape:
    {
      "goal": "...",
      "steps": [
        {
          "id": 1,
          "description": "...",
          "type": "...",
          "target": ".",
          "output_path": "optional"
        }
      ]
    }
    """
    system = (
        "You are a planning engine for a local-first agent system. "
        "Break a user goal into clear executable steps. "
        "Return only raw JSON. Do not include markdown, explanation, or any text before or after the JSON."
    )

    prompt = f"""
Create an execution plan for this goal:

Goal:
{goal}

Return JSON only in this format:

{{
  "goal": "{goal}",
  "steps": [
    {{
      "id": 1,
      "description": "short concrete step",
      "type": "scan_directory | read_file | summarize_repo | summarize_file | write_output | manual_review",
      "target": ".",
      "output_path": "optional output path"
    }}
  ]
}}

Rules:
- Keep steps concrete and minimal
- Prefer executable actions over vague analysis
- Use "scan_directory" for inspecting a repo or folder
- Use "read_file" for reading a specific file
- Use "summarize_repo" for repo or project summaries
- Use "summarize_file" for explaining one file
- Use "write_output" for saving final output
- Use "manual_review" only if absolutely necessary
- Default target to "." when the repo root is implied
- Return JSON only
""".strip()

    data = ask_llm_json(prompt=prompt, model=model, system=system)

    if "goal" not in data or not isinstance(data["goal"], str):
        data["goal"] = goal

    if "steps" not in data or not isinstance(data["steps"], list):
        data["steps"] = []

    return data


def generate_repo_explanation(repo_text: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate a practical summary of a repository from listing + README/context text.
    """
    system = (
        "You are a precise software analyst. "
        "Explain repositories in a clean, practical, engineering-focused way."
    )

    prompt = f"""
Analyze the following repository information and explain:

1. What this project appears to do
2. Its likely architecture
3. Key components or modules
4. What a developer should look at first
5. Any obvious gaps, risks, or next steps

Repository information:
{repo_text}
""".strip()

    return ask_llm(prompt=prompt, model=model, system=system)


def generate_file_explanation(
    file_path: str,
    file_contents: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Generate a practical explanation of a single source file.
    """
    system = (
        "You are a senior software engineer explaining source files. "
        "Be direct, structured, and useful."
    )

    prompt = f"""
Explain this file for a developer.

File path:
{file_path}

File contents:
{file_contents}

Provide:
1. Purpose of the file
2. Important functions or classes
3. Inputs and outputs
4. Risks or issues
5. Suggested improvements
""".strip()

    return ask_llm(prompt=prompt, model=model, system=system)


def generate_step_execution_plan(
    step: Dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Route one step to a concrete executor action.
    Expected return shape:
    {
      "action": "scan_directory" | "read_file" | "summarize_repo" | "summarize_file" | "write_output" | "noop",
      "reason": "short explanation",
      "target": "optional path",
      "output_path": "optional output path",
      "content": "optional text content"
    }
    """
    system = (
        "You are an execution router for a local-first agent system. "
        "Return only raw JSON. Do not include markdown, explanation, or any text before or after the JSON."
    )

    prompt = f"""
You are given one execution step from a plan.

Step:
{json.dumps(step, indent=2)}

Return a JSON object with this exact shape:

{{
  "action": "scan_directory | read_file | summarize_repo | summarize_file | write_output | noop",
  "reason": "short explanation",
  "target": "optional path",
  "output_path": "optional output file path",
  "content": "optional text content to write"
}}

Rules:
- If the step is about scanning a repo or folder, use "scan_directory"
- If the step is about reading a file, use "read_file"
- If the step is about summarizing a repo, use "summarize_repo"
- If the step is about explaining or summarizing a file, use "summarize_file"
- If the step is about saving final output, use "write_output"
- If unclear, use "noop"
- Return JSON only
""".strip()

    data = ask_llm_json(prompt=prompt, model=model, system=system)

    if "action" not in data or not isinstance(data["action"], str):
        data["action"] = "noop"

    if "reason" not in data or not isinstance(data["reason"], str):
        data["reason"] = "No reason provided by model."

    return data