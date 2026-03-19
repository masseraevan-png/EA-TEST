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
from research_pipeline.strategies.mean_reversion import MeanReversionAfterExpansionStrategy
from research_pipeline.strategies.session_breakout import SessionBreakoutStrategy


STRATEGIES = {
    "session_breakout": SessionBreakoutStrategy,
    "mean_reversion_after_expansion": MeanReversionAfterExpansionStrategy,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small bounded real-data research pass.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--mode", choices=["demo_mode", "real_research_mode"], default="real_research_mode")
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "base_config.yaml"))
    parser.add_argument("--max-params-per-strategy", type=int, default=2)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    config = load_config(Path(args.config))
    run_mode = config.resolve_run_mode(args.mode)
    split = config.split
    start = args.start or split["test_start"]
    end = args.end or split["test_end"]

    runner = BacktestRunner(repo_root=REPO_ROOT, config=config, run_mode=run_mode)
    run_rows: list[dict[str, object]] = []
    for strategy_name, strategy_cls in STRATEGIES.items():
        strategy = strategy_cls()
        for parameter_index, parameters in enumerate(strategy.parameter_grid()[: args.max_params_per_strategy]):
            artifacts = runner.run(
                strategy=strategy,
                parameters=parameters,
                symbols=[args.symbol],
                timeframe=args.timeframe,
                start=start,
                end=end,
            )
            average_explicit_cost_per_trade = (
                float(
                    (
                        artifacts.trades["spread_cost_usd"]
                        + artifacts.trades["slippage_cost_usd"]
                        + artifacts.trades["commission_cost_usd"]
                    ).mean()
                )
                if not artifacts.trades.empty
                else 0.0
            )
            quality = artifacts.data_quality[args.symbol]
            run_rows.append(
                {
                    "strategy_name": strategy_name,
                    "parameter_index": parameter_index,
                    "parameters": parameters,
                    "trade_count": artifacts.metrics.total_trades,
                    "total_return": artifacts.metrics.total_return,
                    "profit_factor": artifacts.metrics.profit_factor,
                    "max_drawdown": artifacts.metrics.max_drawdown,
                    "return_to_max_drawdown": artifacts.metrics.return_to_max_drawdown,
                    "avg_explicit_cost_per_trade": average_explicit_cost_per_trade,
                    "data_quality_status": quality["status"],
                    "data_quality_warnings": quality["warning_count"],
                }
            )

    reporter = ReportWriter(REPO_ROOT)
    paths = reporter.write_bounded_research_outputs(
        symbol=args.symbol,
        timeframe=args.timeframe,
        run_mode=run_mode,
        start=start,
        end=end,
        run_rows=run_rows,
    )

    print("Completed bounded research pass")
    print(f"Run mode: {run_mode}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Backtest window: {start} -> {end}")
    for row in run_rows:
        print(
            f"{row['strategy_name']}[param={row['parameter_index']}] trades={row['trade_count']} "
            f"return={row['total_return']:.2f} pf={row['profit_factor']:.2f} "
            f"max_dd={row['max_drawdown']:.2f} return/max_dd={row['return_to_max_drawdown']:.2f} "
            f"avg_cost={row['avg_explicit_cost_per_trade']:.2f}"
        )
    print(f"Report: {paths['report']}")
    print(f"Runs CSV: {paths['runs']}")
    print(f"Best CSV: {paths['best']}")


if __name__ == "__main__":
    main()
