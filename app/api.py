from uuid import uuid4
from pathlib import Path
import json
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from app.ollama_client import generate_plan_steps
from app.executor import generate_repo_summary

app = FastAPI(title="TALOS API", version="0.3-alpha")

PLAN_STORE = {}

DATA_DIR = Path("data")
PLANS_DIR = DATA_DIR / "plans"
OUTPUTS_DIR = DATA_DIR / "outputs"
LOGS_DIR = DATA_DIR / "logs"

for directory in [PLANS_DIR, OUTPUTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class GoalRequest(BaseModel):
    goal: str


class ApprovalRequest(BaseModel):
    plan_id: str
    approved: bool = True


class RunRequest(BaseModel):
    plan_id: str


def _timestamp():
    return datetime.utcnow().isoformat() + "Z"


def _plan_json_path(plan_id: str) -> Path:
    return PLANS_DIR / f"{plan_id}.json"


def _output_txt_path(plan_id: str) -> Path:
    return OUTPUTS_DIR / f"{plan_id}.txt"


def _log_json_path(plan_id: str) -> Path:
    return LOGS_DIR / f"{plan_id}.json"


def _save_plan(plan: dict):
    _plan_json_path(plan["plan_id"]).write_text(
        json.dumps(plan, indent=2),
        encoding="utf-8",
    )


def _save_log(plan_id: str, event: str, payload: dict):
    log_path = _log_json_path(plan_id)

    existing = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []

    existing.append(
        {
            "timestamp": _timestamp(),
            "event": event,
            "payload": payload,
        }
    )

    log_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def create_plan_data(goal: str):
    goal = goal.strip()

    if not goal:
        return {
            "ok": False,
            "error": "Goal cannot be empty",
        }

    plan_id = str(uuid4())
    plan_steps = generate_plan_steps(goal)

    fallback_steps = [
        "Analyze the request",
        "Break the goal into steps",
        "Prepare for approval-gated execution",
    ]

    used_fallback = plan_steps == fallback_steps

    plan_data = {
        "plan_id": plan_id,
        "goal": goal,
        "plan": plan_steps,
        "source": "fallback" if used_fallback else "ollama",
        "status": "draft",
        "approved": False,
        "result": None,
        "created_at": _timestamp(),
        "updated_at": _timestamp(),
    }

    PLAN_STORE[plan_id] = plan_data
    _save_plan(plan_data)
    _save_log(
        plan_id,
        "plan_created",
        {
            "goal": goal,
            "source": plan_data["source"],
        },
    )

    return {
        "ok": True,
        **plan_data,
    }


def approve_plan_data(plan_id: str, approved: bool):
    plan = PLAN_STORE.get(plan_id)

    if not plan:
        plan_path = _plan_json_path(plan_id)
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            PLAN_STORE[plan_id] = plan

    if not plan:
        return {
            "ok": False,
            "error": "Plan not found",
        }

    if approved:
        plan["approved"] = True
        plan["status"] = "approved"
    else:
        plan["approved"] = False
        plan["status"] = "rejected"

    plan["updated_at"] = _timestamp()

    PLAN_STORE[plan_id] = plan
    _save_plan(plan)
    _save_log(
        plan_id,
        "plan_approval_updated",
        {
            "approved": approved,
            "status": plan["status"],
        },
    )

    return {
        "ok": True,
        **plan,
    }


def get_plan_data(plan_id: str):
    plan = PLAN_STORE.get(plan_id)

    if not plan:
        plan_path = _plan_json_path(plan_id)
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            PLAN_STORE[plan_id] = plan

    if not plan:
        return {
            "ok": False,
            "error": "Plan not found",
        }

    return {
        "ok": True,
        **plan,
    }


def run_plan_data(plan_id: str):
    plan = PLAN_STORE.get(plan_id)

    if not plan:
        plan_path = _plan_json_path(plan_id)
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            PLAN_STORE[plan_id] = plan

    if not plan:
        return {
            "ok": False,
            "error": "Plan not found",
        }

    if not plan.get("approved"):
        return {
            "ok": False,
            "error": "Plan must be approved before running",
        }

    goal_lower = plan["goal"].lower()

    if any(word in goal_lower for word in ["repository", "repo", "summarize", "contributor", "review"]):
        result_text = generate_repo_summary(".")
        execution_mode = "repo_summary"
    else:
        result_text = (
            f"TALOS executed plan for goal: {plan['goal']}\n\n"
            f"Plan source: {plan['source']}\n\n"
            f"Steps:\n- " + "\n- ".join(plan["plan"])
        )
        execution_mode = "fallback"

    plan["status"] = "completed"
    plan["result"] = result_text
    plan["updated_at"] = _timestamp()

    _output_txt_path(plan_id).write_text(result_text, encoding="utf-8")
    PLAN_STORE[plan_id] = plan
    _save_plan(plan)
    _save_log(
        plan_id,
        "plan_completed",
        {
            "status": plan["status"],
            "source": plan["source"],
            "execution_mode": execution_mode,
            "output_file": str(_output_txt_path(plan_id)),
        },
    )

    return {
        "ok": True,
        **plan,
        "execution_mode": execution_mode,
        "output_file": str(_output_txt_path(plan_id)),
        "plan_file": str(_plan_json_path(plan_id)),
        "log_file": str(_log_json_path(plan_id)),
    }


@app.get("/")
def root():
    return {
        "ok": True,
        "name": "TALOS API",
        "version": "0.3-alpha",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "status": "healthy",
    }


@app.get("/capabilities")
def capabilities():
    return {
        "ok": True,
        "capabilities": [
            "plan_creation",
            "approval_gating",
            "plan_execution",
            "in_memory_plan_store",
            "disk_persistence",
            "ollama_planning",
        ],
    }


@app.post("/plan")
def create_plan(request: GoalRequest):
    return create_plan_data(request.goal)


@app.get("/plan/{plan_id}")
def get_plan(plan_id: str):
    return get_plan_data(plan_id)


@app.post("/approve")
def approve_plan(request: ApprovalRequest):
    return approve_plan_data(request.plan_id, request.approved)


@app.post("/run")
def run_plan(request: RunRequest):
    return run_plan_data(request.plan_id)