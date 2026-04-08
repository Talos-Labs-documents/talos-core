from app.api import create_plan_data, approve_plan_data, get_plan_data, run_plan_data

current_plan_id = None


def main():
    global current_plan_id

    print("\nTALOS Control Interface - Public Alpha\n")
    print("Type 'help' to begin.\n")

    while True:
        try:
            command = input("talos> ").strip()

            if command in ["exit", "quit"]:
                print("Exiting TALOS.")
                break

            elif command == "help":
                print("""
Available commands:
- help
- plantask <goal>
- showplan
- approveplan
- rejectplan
- runplan
- exit
""")

            elif command.startswith("plantask "):
                goal = command[len("plantask "):]
                result = create_plan_data(goal)

                if result["ok"]:
                    current_plan_id = result["plan_id"]
                    print("\n[PLAN CREATED]")
                    print(f"Plan ID: {result['plan_id']}")
                    print(f"Goal: {result['goal']}")
                    print(f"Source: {result['source']}")
                    print("Steps:")
                    for i, step in enumerate(result["plan"], 1):
                        print(f"  {i}. {step}")
                    print(f"Status: {result['status']}\n")
                else:
                    print(f"Error: {result['error']}")

            elif command == "showplan":
                if not current_plan_id:
                    print("No current plan. Use: plantask <goal>")
                    continue

                result = get_plan_data(current_plan_id)

                if result["ok"]:
                    print("\n[CURRENT PLAN]")
                    print(f"Plan ID: {result['plan_id']}")
                    print(f"Goal: {result['goal']}")
                    print(f"Source: {result['source']}")
                    print("Steps:")
                    for i, step in enumerate(result["plan"], 1):
                        print(f"  {i}. {step}")
                    print(f"Approved: {result['approved']}")
                    print(f"Status: {result['status']}")

                    if result.get("step_results"):
                        print("\nStep Results:")
                        for step in result["step_results"]:
                            executor_name = step.get("executor")
                            line = f"  {step['step_number']}. [{step['status']}] {step['step_text']}"
                            if executor_name:
                                line += f" ({executor_name})"
                            print(line)

                            if step.get("details"):
                                print(f"     -> {step['details']}")

                    if result.get("result"):
                        print(f"\nResult:\n{result['result']}")
                    print()
                else:
                    print(f"Error: {result['error']}")

            elif command == "approveplan":
                if not current_plan_id:
                    print("No current plan to approve.")
                    continue

                result = approve_plan_data(current_plan_id, True)

                if result["ok"]:
                    print(f"Plan approved. Status: {result['status']}")
                else:
                    print(f"Error: {result['error']}")

            elif command == "rejectplan":
                if not current_plan_id:
                    print("No current plan to reject.")
                    continue

                result = approve_plan_data(current_plan_id, False)

                if result["ok"]:
                    print(f"Plan rejected. Status: {result['status']}")
                else:
                    print(f"Error: {result['error']}")

            elif command == "runplan":
                if not current_plan_id:
                    print("No current plan to run.")
                    continue

                result = run_plan_data(current_plan_id)

                if result["ok"]:
                    print("\n[PLAN COMPLETED]")
                    print(f"Status: {result['status']}")
                    print(f"Execution mode: {result.get('execution_mode', 'N/A')}")
                    print(f"Result:\n{result['result']}\n")
                    print(f"Plan file: {result.get('plan_file', 'N/A')}")
                    print(f"Output file: {result.get('output_file', 'N/A')}")
                    print(f"Log file: {result.get('log_file', 'N/A')}\n")
                else:
                    print(f"Error: {result['error']}")

            else:
                print("Unknown command. Type 'help'.")

        except KeyboardInterrupt:
            print("\nExiting TALOS.")
            break


if __name__ == "__main__":
    main()