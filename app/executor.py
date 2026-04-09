from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from app.ollama_client import generate_repo_explanation


ALLOWED_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml"}
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
}
MAX_FILES = 20
MAX_CHARS_PER_FILE = 4000
MAX_TOTAL_CHARS = 30000


def build_repo_summary(repo_path: str) -> str:
    """
    Main entry point for the repo explanation demo.
    """
    root = Path(repo_path).expanduser().resolve()

    if not root.exists():
        return f"[ERROR] Path does not exist: {root}"

    if not root.is_dir():
        return f"[ERROR] Path is not a directory: {root}"

    repo_tree, selected_files = scan_repository(root)

    if not selected_files:
        return "[ERROR] No supported files found in this repository."

    repo_content = collect_file_contents(selected_files)

    explanation = generate_repo_explanation(
        repo_name=root.name,
        repo_tree=repo_tree,
        repo_content=repo_content,
    )

    return format_repo_output(root.name, repo_tree, explanation)


def scan_repository(root: Path) -> Tuple[str, List[Path]]:
    """
    Scan the repository and return:
    - a readable file tree
    - a list of selected files to feed into the LLM
    """
    tree_lines: List[str] = []
    selected_files: List[Path] = []

    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        current_path = Path(current_root)
        rel_dir = current_path.relative_to(root)

        depth = 0 if str(rel_dir) == "." else len(rel_dir.parts)
        indent = "  " * depth

        if str(rel_dir) != ".":
            tree_lines.append(f"{indent}{current_path.name}/")

        for filename in sorted(filenames):
            file_path = current_path / filename

            if should_skip_file(file_path):
                continue

            rel_file = file_path.relative_to(root)
            file_indent = "  " * (depth + 1)
            tree_lines.append(f"{file_indent}{filename}")

            if file_path.suffix.lower() in ALLOWED_EXTENSIONS and len(selected_files) < MAX_FILES:
                selected_files.append(file_path)

    tree_output = "\n".join(tree_lines[:300])
    return tree_output, selected_files


def should_skip_file(file_path: Path) -> bool:
    """
    Skip unsupported or obviously noisy files.
    """
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return True

    name = file_path.name.lower()

    if name in {"package-lock.json", "poetry.lock", "yarn.lock"}:
        return True

    try:
        if file_path.stat().st_size > 200_000:
            return True
    except OSError:
        return True

    return False


def collect_file_contents(files: List[Path]) -> str:
    """
    Read a limited amount of content from each selected file.
    """
    chunks: List[str] = []
    total_chars = 0

    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            chunks.append(f"\n--- FILE: {file_path} ---\n[READ ERROR: {exc}]\n")
            continue

        trimmed = content[:MAX_CHARS_PER_FILE]

        block = f"\n--- FILE: {file_path} ---\n{trimmed}\n"
        projected_total = total_chars + len(block)

        if projected_total > MAX_TOTAL_CHARS:
            remaining = MAX_TOTAL_CHARS - total_chars
            if remaining > 200:
                chunks.append(block[:remaining])
            break

        chunks.append(block)
        total_chars += len(block)

    return "\n".join(chunks)


def format_repo_output(repo_name: str, repo_tree: str, explanation: str) -> str:
    """
    Format the final demo output cleanly for terminal use.
    """
    return f"""
{'=' * 72}
TALOS REPO EXPLAINER
{'=' * 72}

Repository:
{repo_name}

Repository Tree:
{repo_tree}

LLM Explanation:
{explanation}

{'=' * 72}
END OF REPORT
{'=' * 72}
""".strip()