from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from research_pipeline.pipeline import ResearchPipeline, STRATEGY_REGISTRY


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full research batch and emit stress artifacts.")
    parser.add_argument("--strategy", choices=sorted(STRATEGY_REGISTRY), default="mean_reversion_after_expansion")
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--mode", choices=["demo_mode", "real_research_mode"], default=None)
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "base_config.yaml"))
    args = parser.parse_args()

    pipeline = ResearchPipeline(repo_root=REPO_ROOT, config_path=Path(args.config), run_mode=args.mode)
    result = pipeline.run_batch(strategy_name=args.strategy, timeframe=args.timeframe, symbols=args.symbols)
    batch = result["batch"]
    print(f"Run mode: {batch.run_mode}")
    print(f"Neighbor pass ratio: {batch.neighbor_pass_ratio:.2f}")
    print(f"Stress-ready report: {result['paths']['report']}")


if __name__ == "__main__":
    main()
