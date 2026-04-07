from pathlib import Path
from typing import List


SAFE_TEXT_FILES = [
    "README.md",
    "app/main.py",
    "app/api.py",
    "app/ollama_client.py",
]


def _read_text_file(path: Path, max_chars: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:max_chars]
    except Exception:
        return ""


def _list_top_level(repo_root: Path) -> List[str]:
    items = []
    for item in sorted(repo_root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if item.name.startswith(".git"):
            continue
        items.append(item.name + ("/" if item.is_dir() else ""))
    return items


def generate_repo_summary(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()

    top_level = _list_top_level(root)

    sections = []
    sections.append("# TALOS Repository Summary\n")

    sections.append("## Top-level structure")
    for item in top_level:
        sections.append(f"- {item}")
    sections.append("")

    sections.append("## Key file summaries")
    for rel_path in SAFE_TEXT_FILES:
        file_path = root / rel_path
        if file_path.exists() and file_path.is_file():
            content = _read_text_file(file_path)
            preview = content[:800].strip()
            sections.append(f"### {rel_path}")
            if preview:
                sections.append("```")
                sections.append(preview)
                sections.append("```")
            else:
                sections.append("(File exists but could not be read.)")
            sections.append("")

    sections.append("## Contributor-facing interpretation")
    sections.append(
        "This repository appears to be an early-alpha local orchestration system named TALOS. "
        "Its current flow centers on a CLI entry point, API-backed planning logic, approval-gated "
        "execution, and persistent storage of plans, logs, and outputs."
    )
    sections.append("")
    sections.append(
        "A new contributor should start by understanding how `app/main.py` drives the CLI loop, "
        "how `app/api.py` manages plan creation/approval/execution, and how outputs are written "
        "under `data/`."
    )
    sections.append("")
    sections.append(
        "The current design emphasizes safety and traceability: TALOS plans first, requires approval, "
        "then executes bounded actions while leaving artifacts on disk."
    )

    return "\n".join(sections)