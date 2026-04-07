- Approval-gated execution
- Persistent storage (plans, logs, outputs)
- FastAPI backend (ready for expansion)

---
# TALOS 0.3 Public Alpha

TALOS is a local-first orchestration layer for approval-gated AI execution.

It turns goals into structured plans, requires user approval before execution, and writes persistent outputs, plans, and logs to disk.

## Installation

```bash
git clone <your-repo>
cd TALOS

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
Run
python -m app.main
Example Usage
plantask summarize this project
showplan
approveplan
runplan
Output Structure
data/
  plans/     # JSON plan definitions
  outputs/   # Execution results
  logs/      # Execution logs
What This Is (and Isn't)
This is:
A working orchestration prototype
A foundation layer for agent systems
A proof-of-concept for approval-gated AI execution
This is NOT (yet):
A full autonomous agent system
A GUI application
A production-ready platform
Roadmap
Real LLM integration (Ollama / local models)
Multi-step execution engine
Modular agent plugins
Web UI / dashboard
Distributed execution
Philosophy

TALOS is not another chatbot.

It is an orchestration layer:

Plans before acting
Requires approval before execution
Leaves a trace of everything it does