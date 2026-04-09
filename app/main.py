from __future__ import annotations

from app.executor import build_repo_summary


BANNER = r"""
TALOS Control Interface - Public Alpha

Type 'help' to begin.
""".strip()


HELP_TEXT = """
Available commands:
  help                  Show this help menu
  explainrepo <path>    Explain a repository in plain English
  exit                  Exit TALOS
  quit                  Exit TALOS
""".strip()


def print_banner() -> None:
    print()
    print(BANNER)
    print()


def print_help() -> None:
    print()
    print(HELP_TEXT)
    print()


def handle_explainrepo(user_input: str) -> None:
    repo_path = user_input[len("explainrepo "):].strip()

    if not repo_path:
        print("[ERROR] Please provide a repository path.")
        print("Example: explainrepo .")
        return

    print()
    print("[RUNNING REPO EXPLAINER]")
    print()

    try:
        result = build_repo_summary(repo_path)
        print(result)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Repo explanation cancelled.")
    except Exception as exc:
        print(f"[ERROR] Failed to explain repository: {exc}")


def main() -> None:
    print_banner()

    while True:
        try:
            user_input = input("talos> ").strip()
        except KeyboardInterrupt:
            print("\nUse 'exit' or 'quit' to leave TALOS.")
            continue
        except EOFError:
            print("\nExiting TALOS.")
            break

        if not user_input:
            continue

        if user_input in {"exit", "quit"}:
            print("Exiting TALOS.")
            break

        elif user_input == "help":
            print_help()

        elif user_input.startswith("explainrepo "):
            handle_explainrepo(user_input)

        elif user_input == "explainrepo":
            print("[ERROR] Please provide a repository path.")
            print("Example: explainrepo .")

        else:
            print(f"[UNKNOWN COMMAND] {user_input}")
            print("Type 'help' to see available commands.")


if __name__ == "__main__":
    main()