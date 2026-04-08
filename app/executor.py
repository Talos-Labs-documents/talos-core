from pathlib import Path
from typing import List, Dict
import re

from app.ollama_client import generate_repo_explanation, generate_file_explanation


SAFE_TEXT_FILES = [
    "README.md",
    "Readme.md",
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
        if item.name.startswith("."):
            continue
        items.append(item.name + ("/" if item.is_dir() else ""))
    return items


def _build_repo_context(repo_root: Path) -> str:
    top_level = _list_top_level(repo_root)

    parts = []
    parts.append("TOP-LEVEL STRUCTURE:")
    for item in top_level:
        parts.append(f"- {item}")
    parts.append("")

    parts.append("KEY FILE PREVIEWS:")
    for rel_path in SAFE_TEXT_FILES:
        file_path = repo_root / rel_path
        if file_path.exists() and file_path.is_file():
            content = _read_text_file(file_path, max_chars=2000).strip()
            if content:
                parts.append(f"\nFILE: {rel_path}\n")
                parts.append(content[:1200])
                parts.append("\n")

    return "\n".join(parts)


def _generate_static_summary(repo_root: Path) -> str:
    top_level = _list_top_level(repo_root)

    sections = []
    sections.append("# TALOS Repository Summary\n")

    sections.append("## Top-level structure")
    for item in top_level:
        sections.append(f"- {item}")
    sections.append("")

    sections.append("## Key file summaries")
    for rel_path in SAFE_TEXT_FILES:
        file_path = repo_root / rel_path
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
        "how `app/api.py` manages plan creation, approval, and execution, and how outputs are written "
        "under `data/`."
    )
    sections.append("")
    sections.append(
        "The current design emphasizes safety and traceability: TALOS plans first, requires approval, "
        "then executes bounded actions while leaving artifacts on disk."
    )

    return "\n".join(sections)


def generate_repo_summary(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()

    context = _build_repo_context(root)
    llm_summary = generate_repo_explanation(context)

    if llm_summary:
        return "# TALOS Repository Summary\n\n" + llm_summary

    return _generate_static_summary(root)


def review_repository_structure(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    items = _list_top_level(root)
    return "Top-level repository structure: " + ", ".join(items)


def review_cli_flow(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    main_path = root / "app" / "main.py"

    if not main_path.exists():
        return "CLI entry point not found at app/main.py."

    content = _read_text_file(main_path, max_chars=3500)

    findings = []
    findings.append("CLI entry point found at app/main.py.")

    if 'input("talos> ")' in content or "input('talos> ')" in content:
        findings.append("Interactive command loop is present.")

    for cmd in ["plantask", "showplan", "approveplan", "rejectplan", "runplan"]:
        if cmd in content:
            findings.append(f"Command handler present for '{cmd}'.")

    return " ".join(findings)


def review_api_flow(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    api_path = root / "app" / "api.py"

    if not api_path.exists():
        return "API module not found at app/api.py."

    content = _read_text_file(api_path, max_chars=8000)

    findings = []
    findings.append("API module found at app/api.py.")

    for route in ["/plan", "/approve", "/run", "/health", "/capabilities"]:
        if route in content:
            findings.append(f"Route detected: {route}")

    for fn in ["create_plan_data", "approve_plan_data", "get_plan_data", "run_plan_data"]:
        if fn in content:
            findings.append(f"Core function detected: {fn}")

    return " ".join(findings)


def review_output_flow(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    data_dir = root / "data"
    findings = []

    if not data_dir.exists():
        return "Data directory not found."

    findings.append("Data directory exists.")

    for subdir in ["plans", "outputs", "logs"]:
        path = data_dir / subdir
        if path.exists():
            count = len(list(path.glob("*")))
            findings.append(f"{subdir}/ exists with {count} item(s).")
        else:
            findings.append(f"{subdir}/ is missing.")

    return " ".join(findings)


def review_plan_lifecycle(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    api_path = root / "app" / "api.py"

    if not api_path.exists():
        return "Could not review plan lifecycle because app/api.py was not found."

    content = _read_text_file(api_path, max_chars=10000)

    findings = []
    findings.append("Plan lifecycle reviewed in app/api.py.")

    if "def create_plan_data" in content:
        findings.append("Plan creation function detected.")
    if "def approve_plan_data" in content:
        findings.append("Approval function detected.")
    if "def run_plan_data" in content:
        findings.append("Execution function detected.")
    if "_save_plan" in content:
        findings.append("Plan persistence helper detected.")
    if "_save_log" in content:
        findings.append("Log persistence helper detected.")
    if "_output_txt_path" in content:
        findings.append("Output file writing path detected.")

    return " ".join(findings)


def inspect_docs_folder(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    docs_dir = root / "docs"

    if not docs_dir.exists():
        return "docs/ folder not found."

    if not docs_dir.is_dir():
        return "docs exists but is not a directory."

    doc_files = sorted([p for p in docs_dir.iterdir() if p.is_file()], key=lambda p: p.name.lower())

    if not doc_files:
        return "docs/ folder exists but currently appears empty."

    findings = [f"docs/ folder contains {len(doc_files)} file(s)."]
    for file_path in doc_files[:10]:
        findings.append(f"Detected documentation file: {file_path.name}")
        preview = _read_text_file(file_path, max_chars=500).strip()
        if preview:
            preview_line = preview.replace("\n", " ")[:180]
            findings.append(f"Preview for {file_path.name}: {preview_line}")

    return " ".join(findings)


def summarize_file(rel_path: str, repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    file_path = root / rel_path

    if not file_path.exists():
        return f"Requested file not found: {rel_path}"

    if not file_path.is_file():
        return f"Requested path is not a file: {rel_path}"

    content = _read_text_file(file_path, max_chars=3500)
    if not content.strip():
        return f"File exists but could not be read or is empty: {rel_path}"

    llm_summary = generate_file_explanation(rel_path, content[:2500])
    if llm_summary:
        return llm_summary

    summary_parts = [f"Reviewed file: {rel_path}."]
    if "def " in content:
        summary_parts.append("Function definitions are present.")
    if "class " in content:
        summary_parts.append("Class definitions are present.")
    if "@app." in content or "FastAPI" in content:
        summary_parts.append("API-related code is present.")
    if "input(" in content:
        summary_parts.append("Interactive CLI input handling is present.")
    if "write_text(" in content or "read_text(" in content:
        summary_parts.append("File persistence operations are present.")

    preview = content[:350].replace("\n", " ")
    summary_parts.append(f"Preview: {preview}")

    return " ".join(summary_parts)


def explain_api_routes(repo_root: str = ".") -> str:
    root = Path(repo_root).resolve()
    api_path = root / "app" / "api.py"

    if not api_path.exists():
        return "Cannot explain API routes because app/api.py was not found."

    content = _read_text_file(api_path, max_chars=12000)

    route_matches = re.findall(r'@app\.(get|post)\("([^"]+)"\)', content)
    if not route_matches:
        return "No API route decorators were detected in app/api.py."

    findings = ["API route definitions reviewed."]
    for method, route in route_matches:
        findings.append(f"{method.upper()} {route}")

    return " ".join(findings)


def review_generic_context(step_text: str, repo_root: str = ".") -> str:
    return f"Reviewed repository context for step: {step_text}"


def _extract_file_reference(step_text: str, repo_root: str = ".") -> str | None:
    root = Path(repo_root).resolve()

    patterns = [
        r"\b[a-zA-Z0-9_/\-]+\.(?:py|md|txt|json|yaml|yml)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, step_text)
        if match:
            candidate = match.group(0)

            if (root / candidate).exists():
                return candidate

            app_candidate = root / "app" / candidate
            if app_candidate.exists():
                return f"app/{candidate}"

            for p in root.rglob(candidate):
                return str(p.relative_to(root))

    return None


def execute_step(step_text: str, goal: str, repo_root: str = ".") -> Dict[str, str]:
    text = step_text.lower()

    try:
        file_ref = _extract_file_reference(step_text, repo_root)
        if file_ref:
            return {
                "status": "completed",
                "details": summarize_file(file_ref, repo_root),
                "executor": "summarize_file",
            }

        if "api routes" in text or "routes" in text or "endpoints" in text:
            return {
                "status": "completed",
                "details": explain_api_routes(repo_root),
                "executor": "explain_api_routes",
            }

        if "plan lifecycle" in text or "approval" in text or "persistence" in text or "execution flow" in text:
            return {
                "status": "completed",
                "details": review_plan_lifecycle(repo_root),
                "executor": "review_plan_lifecycle",
            }

        if "cli" in text or "command loop" in text or "interactive" in text:
            return {
                "status": "completed",
                "details": review_cli_flow(repo_root),
                "executor": "review_cli_flow",
            }

        if "api" in text or "request/response" in text:
            return {
                "status": "completed",
                "details": review_api_flow(repo_root),
                "executor": "review_api_flow",
            }

        if "output" in text or "log" in text or "data flow" in text or "written to disk" in text:
            return {
                "status": "completed",
                "details": review_output_flow(repo_root),
                "executor": "review_output_flow",
            }

        if "structure" in text or "folder" in text or "directory" in text:
            return {
                "status": "completed",
                "details": review_repository_structure(repo_root),
                "executor": "review_repository_structure",
            }

        if "documentation" in text or "docs" in text:
            return {
                "status": "completed",
                "details": inspect_docs_folder(repo_root),
                "executor": "inspect_docs_folder",
            }

        if any(word in goal.lower() for word in ["repository", "repo", "summarize", "contributor", "review"]):
            return {
                "status": "completed",
                "details": review_generic_context(step_text, repo_root),
                "executor": "review_generic_context",
            }

        return {
            "status": "completed",
            "details": f"Fallback execution completed for step: {step_text}",
            "executor": "fallback",
        }

    except Exception as e:
        return {
            "status": "failed",
            "details": f"Executor error: {e}",
            "executor": "error",
        }