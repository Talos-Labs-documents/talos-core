from __future__ import annotations

from app.api import create_plan_data, approve_plan_data, get_plan_data, run_plan_data


def print_help() -> None:
    print(
        "\nCommands:\n"
        "  help                     Show this help message\n"
        "  plantask <goal>          Create a plan for a goal\n"
        "  showplan                 Show the current plan\n"
        "  approveplan              Approve the current plan\n"
        "  runplan                  Run the current plan\n"
        "  exit                     Quit TALOS\n"
    )


def print_plan(result: dict, title: str = "[CURRENT PLAN]") -> None:
    print(f"\n{title}")
    print(f"Plan ID: {result.get('plan_id', 'N/A')}")
    print(f"Goal: {result.get('goal', 'N/A')}")
    print(f"Source: {result.get('source', 'N/A')}")

    steps = result.get("step_results", [])
    print("Steps:")
    if not steps:
        print("  (none)")
    else:
        for step in steps:
            print(f"  {step['step_number']}. {step['step_text']}")

    print(f"Approved: {result.get('approved', False)}")
    print(f"Status: {result.get('status', 'unknown')}")


def print_step_results(result: dict) -> None:
    steps = result.get("step_results", [])
    print("\nStep Results:")
    if not steps:
        print("  (none)")
        return

    for step in steps:
        line = f"  {step['step_number']}. [{step['status']}] {step['step_text']}"
        print(line)
        if step.get("result"):
            print(f"     Result: {step['result']}")


def build_run_summary(result: dict) -> str:
    steps = result.get("step_results", [])
    completed = sum(1 for s in steps if s.get("status") == "success")
    errored = sum(1 for s in steps if s.get("status") == "error")
    skipped = sum(1 for s in steps if s.get("status") == "skipped")
    pending = sum(1 for s in steps if s.get("status") == "pending")

    return (
        f"Goal: {result.get('goal', 'N/A')}\n"
        f"Status: {result.get('status', 'unknown')}\n"
        f"Approved: {result.get('approved', False)}\n"
        f"Steps total: {len(steps)}\n"
        f"Successful: {completed}\n"
        f"Errored: {errored}\n"
        f"Skipped: {skipped}\n"
        f"Pending: {pending}"
    )


def main() -> None:
    current_plan_id = None

    print("TALOS Control Interface - Public Alpha\n")
    print("Type 'help' to begin.\n")

    while True:
        try:
            raw = input("talos> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting TALOS.")
            break

        if not raw:
            continue

        if raw == "exit":
            print("Exiting TALOS.")
            break

        if raw == "help":
            print_help()
            continue

        if raw.startswith("plantask "):
            goal = raw[len("plantask ") :].strip()
            if not goal:
                print("Usage: plantask <goal>")
                continue

            result = create_plan_data(goal)

            if result["ok"]:
                current_plan_id = result["plan_id"]
                print("\n[PLAN CREATED]")
                print(f"Plan ID: {result['plan_id']}")
                print(f"Goal: {result['goal']}")
                print(f"Source: {result['source']}")
                print("Steps:")
                for step in result.get("step_results", []):
                    print(f"  {step['step_number']}. {step['step_text']}")
                print(f"Status: {result['status']}")
            else:
                print(f"Error: {result['error']}")
            continue

        if raw == "showplan":
            result = get_plan_data(current_plan_id)

            if result["ok"]:
                print_plan(result)
                print_step_results(result)
            else:
                print(result["error"])
            continue

        if raw == "approveplan":
            result = approve_plan_data(current_plan_id, True)

            if result["ok"]:
                current_plan_id = result["plan_id"]
                print(f"Plan approved. Status: {result['status']}")
            else:
                print(f"Error: {result['error']}")
            continue

        if raw == "runplan":
            result = run_plan_data(current_plan_id)

            if result["ok"]:
                print("\n[PLAN COMPLETED]")
                print(f"Status: {result.get('status', 'unknown')}")
                print("Execution mode: N/A")
                print(f"Result:\n{build_run_summary(result)}\n")
                print_step_results(result)
            else:
                print(f"Error: {result['error']}")
            continue

        print("Unknown command. Type 'help' to see available commands.")


if __name__ == "__main__":
    main()