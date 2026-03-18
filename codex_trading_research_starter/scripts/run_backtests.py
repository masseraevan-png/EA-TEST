from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    print("Starter placeholder: Codex should replace this with the real backtest runner.")
    print("Read these first:")
    print(" - README.md")
    print(" - RESEARCH_RULES.md")
    print(" - ACCEPTANCE_CRITERIA.md")
    print(" - configs/base_config.yaml")
    print(f"Repo root: {repo_root}")


if __name__ == "__main__":
    main()
