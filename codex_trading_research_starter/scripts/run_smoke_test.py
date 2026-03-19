from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from research_pipeline.backtest import BacktestRunner
from research_pipeline.config import load_config
from research_pipeline.reporting import ReportWriter
from research_pipeline.strategies.session_breakout import SessionBreakoutStrategy


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a lightweight real-data smoke test.")
    parser.add_argument("--strategy", choices=["session_breakout"], default="session_breakout")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--mode", choices=["demo_mode", "real_research_mode"], default="real_research_mode")
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "base_config.yaml"))
    parser.add_argument("--parameter-index", type=int, default=0, help="Index into the strategy parameter grid.")
    parser.add_argument("--start", default=None, help="Override backtest start date.")
    parser.add_argument("--end", default=None, help="Override backtest end date.")
    args = parser.parse_args()

    if args.strategy != "session_breakout":
        raise ValueError("Smoke test runner currently supports only session_breakout.")

    config = load_config(Path(args.config))
    run_mode = config.resolve_run_mode(args.mode)
    strategy = SessionBreakoutStrategy()
    parameter_grid = strategy.parameter_grid()
    if args.parameter_index < 0 or args.parameter_index >= len(parameter_grid):
        raise IndexError(f"--parameter-index must be between 0 and {len(parameter_grid) - 1}")
    parameters = parameter_grid[args.parameter_index]

    split = config.split
    start = args.start or split["test_start"]
    end = args.end or split["test_end"]

    runner = BacktestRunner(repo_root=REPO_ROOT, config=config, run_mode=run_mode)
    artifacts = runner.run(
        strategy=strategy,
        parameters=parameters,
        symbols=[args.symbol],
        timeframe=args.timeframe,
        start=start,
        end=end,
    )

    skipped_steps = [
        "Broad parameter sweep",
        "Neighbor sensitivity grid",
        "Full walk-forward validation",
        "Full stress-test matrix",
        "Holdout, validation, and train batch orchestration",
    ]
    reporter = ReportWriter(REPO_ROOT)
    paths = reporter.write_smoke_test_outputs(
        strategy_name=args.strategy,
        run_mode=run_mode,
        timeframe=args.timeframe,
        symbols=[args.symbol],
        start=start,
        end=end,
        parameters=parameters,
        artifacts=artifacts,
        skipped_steps=skipped_steps,
    )

    print(f"Completed lightweight smoke test for {args.strategy}")
    print(f"Run mode: {run_mode}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Backtest window: {start} -> {end}")
    print(f"Parameters: {parameters}")
    print(f"Trades: {artifacts.metrics.total_trades}")
    print(f"Total return: {artifacts.metrics.total_return:.2f}")
    print(f"Profit factor: {artifacts.metrics.profit_factor:.2f}")
    print(f"Report: {paths['report']}")
    print(f"Trade log: {paths['trade_log']}")
    print(f"Equity curve: {paths['equity_curve']}")
    print(f"Monthly returns: {paths['monthly_returns']}")
    print(f"Summary JSON: {paths['summary']}")


if __name__ == "__main__":
    main()
