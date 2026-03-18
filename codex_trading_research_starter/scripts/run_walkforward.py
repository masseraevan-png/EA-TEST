from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    print("Starter placeholder: Codex should replace this with the real walk-forward runner.")
    print("This script should eventually:")
    print(" - optimize on train")
    print(" - validate on validation")
    print(" - evaluate on test")
    print(" - keep holdout untouched until final check")
    print(f"Repo root: {repo_root}")


if __name__ == "__main__":
    main()
