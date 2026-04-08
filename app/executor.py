from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.ollama_client import (
    generate_file_explanation,
    generate_repo_explanation,
    generate_step_execution_plan,
)


DATA_OUTPUT_DIR = Path("data/outputs")

IGNORE_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".tox",
    ".eggs",
}

IGNORE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".o",
    ".a",
    ".class",
}

PREFERRED_SCAN_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".env",
}


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def should_ignore_path(path: Path) -> bool:
    parts = set(path.parts)

    if parts & IGNORE_DIRS:
        return True

    if path.is_file() and path.suffix.lower() in IGNORE_FILE_SUFFIXES:
        return True

    return False


def should_include_file_in_scan(path: Path) -> bool:
    if not path.is_file():
        return True

    if should_ignore_path(path):
        return False

    # Keep common project files even if they have no suffix
    name = path.name.lower()
    if name in {
        "readme",
        "license",
        "dockerfile",
        "makefile",
        ".gitignore",
        ".env",
        ".env.example",
        "requirements.txt",
        "pyproject.toml",
    }:
        return True

    if path.suffix.lower() in PREFERRED_SCAN_SUFFIXES:
        return True

    return False


def resolve_path(target: str, repo_root: str = ".") -> Path:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path
    return (Path(repo_root) / target_path).resolve()


def scan_directory(path: Path) -> str:
    if not path.exists():
        return f"Path does not exist: {path}"

    if not path.is_dir():
        return f"Path is not a directory: {path}"

    lines: List[str] = []

    for p in sorted(path.rglob("*")):
        if should_ignore_path(p):
            continue

        if p.is_file() and not should_include_file_in_scan(p):
            continue

        try:
            rel = p.relative_to(path)
        except ValueError:
            rel = p

        if p.is_dir():
            lines.append(f"[DIR]  {rel}")
        else:
            lines.append(f"[FILE] {rel}")

    if not lines:
        return f"No relevant files found in: {path}"

    return "\n".join(lines)


def write_output(path: Path, content: str) -> str:
    ensure_parent_dir(path)
    path.write_text(content, encoding="utf-8")
    return f"Wrote output to {path}"


def find_readme(repo_path: Path) -> str:
    readme_candidates = [
        repo_path / "README.md",
        repo_path / "readme.md",
        repo_path / "README.txt",
        repo_path / "README",
    ]

    for candidate in readme_candidates:
        if candidate.exists() and candidate.is_file():
            return safe_read_text(candidate)

    return ""


def summarize_repository(repo_path: Path) -> str:
    listing = scan_directory(repo_path)
    readme_text = find_readme(repo_path)

    repo_text = f"""
Repository path: {repo_path}

Directory listing:
{listing}

README:
{readme_text}
""".strip()

    return generate_repo_explanation(repo_text)


def summarize_file(file_path: Path) -> str:
    if not file_path.exists():
        return f"File not found: {file_path}"

    if not file_path.is_file():
        return f"Path is not a file: {file_path}"

    contents = safe_read_text(file_path)
    return generate_file_explanation(str(file_path), contents)


def normalize_step(step: Any) -> Dict[str, Any]:
    if isinstance(step, dict):
        return step

    if isinstance(step, str):
        return {"description": step}

    return {"description": str(step)}


def infer_target_from_step(step: Dict[str, Any]) -> str:
    for key in ("target", "path", "file_path", "repo_path"):
        value = step.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    description = str(step.get("description", "")).strip()
    return description or "."


def fallback_execution_plan(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple keyword fallback in case the router returns junk or noop.
    """
    description = str(step.get("description", "")).lower()
    target = infer_target_from_step(step)
    step_type = str(step.get("type", "")).lower()
    output_path = step.get("output_path")

    text = f"{description} {step_type}".strip()

    if "scan" in text or "directory" in text or "structure" in text:
        return {
            "action": "scan_directory",
            "reason": "Fallback rule matched scan/directory language.",
            "target": target,
            "output_path": output_path,
            "content": "",
        }

    if "summarize repo" in text or "summarize the repository" in text or "repository" in text:
        return {
            "action": "summarize_repo",
            "reason": "Fallback rule matched repository summary language.",
            "target": target,
            "output_path": output_path,
            "content": "",
        }

    if "read file" in text or step_type == "read_file":
        return {
            "action": "read_file",
            "reason": "Fallback rule matched file-read language.",
            "target": target,
            "output_path": output_path,
            "content": "",
        }

    if "summarize file" in text or "explain file" in text or step_type == "summarize_file":
        return {
            "action": "summarize_file",
            "reason": "Fallback rule matched file summary language.",
            "target": target,
            "output_path": output_path,
            "content": "",
        }

    if "write" in text or "save" in text or step_type == "write_output":
        return {
            "action": "write_output",
            "reason": "Fallback rule matched write/save language.",
            "target": target,
            "output_path": output_path or str(DATA_OUTPUT_DIR / "summary.txt"),
            "content": "",
        }

    return {
        "action": "noop",
        "reason": "No fallback rule matched.",
        "target": target,
        "output_path": output_path,
        "content": "",
    }


def choose_execution_plan(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM router first, then fall back to deterministic rules if needed.
    """
    try:
        llm_plan = generate_step_execution_plan(step)

        if not isinstance(llm_plan, dict):
            return fallback_execution_plan(step)

        action = llm_plan.get("action", "noop")
        if not isinstance(action, str) or not action.strip():
            return fallback_execution_plan(step)

        # If router gives noop for a clearly structured step, fallback may be better
        if action == "noop":
            fb = fallback_execution_plan(step)
            if fb["action"] != "noop":
                return fb

        llm_plan.setdefault("reason", "No reason provided.")
        llm_plan.setdefault("target", infer_target_from_step(step))
        llm_plan.setdefault("output_path", step.get("output_path"))
        llm_plan.setdefault("content", "")
        return llm_plan

    except Exception as e:
        fb = fallback_execution_plan(step)
        fb["reason"] = f"{fb['reason']} Router fallback used after error: {e}"
        return fb


def execute_step(step: Dict[str, Any], repo_root: str = ".") -> Dict[str, Any]:
    step = normalize_step(step)

    execution_plan = choose_execution_plan(step)
    action = execution_plan.get("action", "noop")
    target = execution_plan.get("target") or infer_target_from_step(step)
    output_path = execution_plan.get("output_path")
    content = execution_plan.get("content", "")

    result: Dict[str, Any] = {
        "step": step,
        "execution_plan": execution_plan,
        "status": "success",
        "result": "",
    }

    try:
        if action == "scan_directory":
            resolved_target = resolve_path(target, repo_root)
            result["result"] = scan_directory(resolved_target)

        elif action == "read_file":
            resolved_target = resolve_path(target, repo_root)
            result["result"] = safe_read_text(resolved_target)

        elif action == "summarize_repo":
            resolved_target = resolve_path(target, repo_root)
            summary = summarize_repository(resolved_target)
            result["result"] = summary

            if output_path:
                resolved_output = resolve_path(output_path, repo_root)
                write_output(resolved_output, summary)

        elif action == "summarize_file":
            resolved_target = resolve_path(target, repo_root)
            summary = summarize_file(resolved_target)
            result["result"] = summary

            if output_path:
                resolved_output = resolve_path(output_path, repo_root)
                write_output(resolved_output, summary)

        elif action == "write_output":
            final_output = content or f"Step completed:\n{json.dumps(step, indent=2)}"
            resolved_output = resolve_path(
                output_path or str(DATA_OUTPUT_DIR / "summary.txt"),
                repo_root,
            )
            result["result"] = write_output(resolved_output, final_output)

        else:
            result["status"] = "skipped"
            result["result"] = f"No executable action chosen. Router returned: {action}"

    except Exception as e:
        result["status"] = "error"
        result["result"] = str(e)

    return result


def generate_repo_summary(repo_path: str = ".") -> str:
    resolved_repo = Path(repo_path).resolve()
    summary = summarize_repository(resolved_repo)
    output_path = DATA_OUTPUT_DIR / "summary.txt"
    write_output(output_path, summary)
    return summary