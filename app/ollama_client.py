import json
import requests
from typing import Optional


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"


def generate_text(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 180) -> str:
    """
    Send a prompt to Ollama and return the generated text.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()


def generate_repo_explanation(repo_name: str, repo_tree: str, repo_content: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate a plain-English explanation of a repository.
    """
    prompt = f"""
You are an expert software analyst.

Your job is to explain a code repository in plain English for a technical but practical user.

Repository name:
{repo_name}

Repository file tree:
{repo_tree}

Selected repository file contents:
{repo_content}

Please respond in this exact structure:

Project Name:
<name>

Purpose:
<what this project appears to do>

Main Components:
- <component 1>
- <component 2>
- <component 3>

How It Works:
1. <step 1>
2. <step 2>
3. <step 3>

Important Files:
- <filename>: <what it does>
- <filename>: <what it does>

Best Guess Summary:
<2-5 sentence summary>

Be concrete. Do not be vague. If something is unclear, say "best guess" instead of inventing facts.
""".strip()

    return generate_text(prompt, model=model)


def generate_file_explanation(file_path: str, file_content: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generate an explanation of a single file.
    """
    prompt = f"""
You are an expert software analyst.

Explain this file in plain English.

File path:
{file_path}

File content:
{file_content}

Return:
- Purpose
- Key functions/classes
- Inputs/outputs
- Notes
""".strip()

    return generate_text(prompt, model=model)