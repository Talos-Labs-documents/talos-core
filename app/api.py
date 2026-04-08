from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.executor import execute_step
from app.ollama_client import generate_plan_steps


PLANS: Dict[str, Dict[str, Any]] = {}


def _normalize_step(step: Any, index: int) -> Dict[str, Any]:
    if isinstance(step, dict):
        return {
            "id": step.get("id", index),
            "description": step.get("description", f"Step {index}"),
            "type": step.get("type", "manual_review"),
            "target": step.get("target", "."),
            "output_path": step.get("output_path"),
            "status": step.get("status", "pending"),
            "result": step.get("result"),
            "execution_plan": step.get("execution_plan"),
        }

    return {
        "id": index,
        "description": str(step),
        "type": "manual_review",
        "target": ".",
        "output_path": None,
        "status": "pending",
        "result": None,
        "execution_plan": None,
    }


def _normalize_steps(raw_steps: List[Any]) -> List[Dict[str, Any]]:
    return [_normalize_step(step, i) for i, step in enumerate(raw_steps, start=1)]


def _latest_plan() -> Optional[Dict[str, Any]]:
    if not PLANS:
        return None
    last_plan_id = list(PLANS.keys())[-1]
    return PLANS[last_plan_id]


def _legacy_steps(plan: Dict[str, Any]) -> List[str]:
    return [
        step.get("description", f"Step {i}")
        for i, step in enumerate(plan.get("plan_steps", []), start=1)
    ]


def _legacy_step_results(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for i, step in enumerate(plan.get("plan_steps", []), start=1):
        results.append(
            {
                "step_number": i,
                "step_text": step.get("description", f"Step {i}"),
                "status": step.get("status", "pending"),
                "result": step.get("result"),
            }
        )

    return results


def _build_result_summary(plan: Dict[str, Any]) -> str:
    lines: List[str] = []

    for i, step in enumerate(plan.get("plan_steps", []), start=1):
        description = step.get("description", f"Step {i}")
        status = step.get("status", "pending")
        lines.append(f"{i}. {description} -> {status}")

        step_result = step.get("result")
        if step_result:
            cleaned = str(step_result).strip()
            if cleaned:
                lines.append(cleaned)

    if not lines:
        return "No step results available."

    return "\n\n".join(lines)


def _wrap_plan(plan: Dict[str, Any], message: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "ok": True,
        "plan_id": plan["plan_id"],
        "goal": plan["goal"],
        "source": plan.get("source", "ollama"),
        "repo_root": plan.get("repo_root", "."),
        "steps": _legacy_steps(plan),
        "approved": plan.get("approved", False),
        "status": plan.get("status", "draft"),
        "step_results": _legacy_step_results(plan),
        "result": _build_result_summary(plan),
        "plan": plan,
    }

    if message:
        payload["message"] = message

    return payload


def _wrap_error(message: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": message,
    }


def create_plan_data(goal: str, repo_root: str = ".") -> Dict[str, Any]:
    try:
        generated_plan = generate_plan_steps(goal)
        raw_steps = generated_plan.get("steps", [])
        normalized_steps = _normalize_steps(raw_steps)

        plan_id = str(uuid.uuid4())
        plan: Dict[str, Any] = {
            "plan_id": plan_id,
            "goal": generated_plan.get("goal", goal),
            "source": "ollama",
            "repo_root": repo_root,
            "plan_steps": normalized_steps,
            "approved": False,
            "status": "draft",
        }

        PLANS[plan_id] = plan
        return _wrap_plan(plan)

    except Exception as e:
        return _wrap_error(f"Failed to create plan: {e}")


def get_plan_data(plan_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        if plan_id:
            plan = PLANS.get(plan_id)
            if not plan:
                return _wrap_error(f"Plan not found: {plan_id}")
            return _wrap_plan(plan)

        plan = _latest_plan()
        if not plan:
            return _wrap_error("No current plan. Use: plantask <goal>")

        return _wrap_plan(plan)

    except Exception as e:
        return _wrap_error(f"Failed to get plan: {e}")


def approve_plan_data(plan_id: Optional[str] = None, approved: bool = True) -> Dict[str, Any]:
    try:
        if plan_id:
            plan = PLANS.get(plan_id)
        else:
            plan = _latest_plan()

        if not plan:
            return _wrap_error("No current plan to approve.")

        plan["approved"] = bool(approved)
        plan["status"] = "approved" if approved else "draft"

        return _wrap_plan(plan, message=f"Plan {'approved' if approved else 'unapproved'}.")

    except Exception as e:
        return _wrap_error(f"Failed to approve plan: {e}")


def run_plan_data(plan_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        if plan_id:
            plan = PLANS.get(plan_id)
        else:
            plan = _latest_plan()

        if not plan:
            return _wrap_error("No current plan to run.")

        if not plan.get("approved", False):
            return _wrap_error("Plan must be approved before execution.")

        repo_root = plan.get("repo_root", ".")
        plan["status"] = "running"

        for step in plan.get("plan_steps", []):
            step_result = execute_step(step, repo_root=repo_root)

            step["status"] = step_result.get("status", "success")
            step["result"] = step_result.get("result", "")
            step["execution_plan"] = step_result.get("execution_plan", {})

            if step["status"] == "error":
                plan["status"] = "error"
                return _wrap_plan(plan, message="Execution stopped on error.")

        plan["status"] = "completed"
        return _wrap_plan(plan, message="Execution completed.")

    except Exception as e:
        return _wrap_error(f"Execution failed: {e}")