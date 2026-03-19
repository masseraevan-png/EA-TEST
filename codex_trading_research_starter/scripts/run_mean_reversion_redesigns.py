from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from research_pipeline.backtest import BacktestRunner
from research_pipeline.config import load_config
from research_pipeline.strategies.mean_reversion import (
    MeanReversionAfterExpansionStrategy,
    MeanReversionExhaustionWickStrategy,
    MeanReversionFailedFollowThroughStrategy,
)


def render_report(rows: list[dict[str, object]], symbol: str, timeframe: str, run_mode: str, start: str, end: str) -> str:
    lines = "\n".join(
        f"| {row['label']} | {row['trade_count']} | {row['avg_gross_pnl_per_trade']:.2f} | "
        f"{row['avg_net_pnl_per_trade']:.2f} | {row['profit_factor']:.2f} | "
        f"{row['max_drawdown']:.2f} | {row['avg_explicit_cost_per_trade']:.2f} |"
        for row in rows
    )
    return f"""# Mean Reversion Redesign Report

## 1. Scope
- Symbol: {symbol}
- Timeframe: {timeframe}
- Run mode: {run_mode}
- Backtest window: {start} to {end}
- Baseline: mean_reversion_after_expansion parameter set 1 only
- Redesigns tested: exhaustion wick, failed follow-through

## 2. Compact comparison
| Variant | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|
{lines}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a compact redesign comparison for mean-reversion variants.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--mode", choices=["demo_mode", "real_research_mode"], default="real_research_mode")
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "base_config.yaml"))
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    config = load_config(Path(args.config))
    run_mode = config.resolve_run_mode(args.mode)
    split = config.split
    start = args.start or split["test_start"]
    end = args.end or split["test_end"]
    runner = BacktestRunner(repo_root=REPO_ROOT, config=config, run_mode=run_mode)

    variants = [
        (
            "baseline_param_1",
            MeanReversionAfterExpansionStrategy(),
            MeanReversionAfterExpansionStrategy().parameter_grid()[1],
        ),
        (
            "redesign_exhaustion_wick",
            MeanReversionExhaustionWickStrategy(),
            MeanReversionExhaustionWickStrategy().parameter_grid()[0],
        ),
        (
            "redesign_failed_follow_through",
            MeanReversionFailedFollowThroughStrategy(),
            MeanReversionFailedFollowThroughStrategy().parameter_grid()[0],
        ),
    ]

    rows: list[dict[str, object]] = []
    for label, strategy, parameters in variants:
        artifacts = runner.run(
            strategy=strategy,
            parameters=parameters,
            symbols=[args.symbol],
            timeframe=args.timeframe,
            start=start,
            end=end,
        )
        trades = artifacts.trades
        total_cost = trades["spread_cost_usd"] + trades["slippage_cost_usd"] + trades["commission_cost_usd"]
        rows.append(
            {
                "label": label,
                "strategy_name": strategy.spec.name,
                "parameters": parameters,
                "trade_count": int(artifacts.metrics.total_trades),
                "avg_gross_pnl_per_trade": float(trades["gross_pnl_usd"].mean()) if not trades.empty else 0.0,
                "avg_net_pnl_per_trade": float(trades["pnl"].mean()) if not trades.empty else 0.0,
                "profit_factor": float(artifacts.metrics.profit_factor),
                "max_drawdown": float(artifacts.metrics.max_drawdown),
                "avg_explicit_cost_per_trade": float(total_cost.mean()) if not trades.empty else 0.0,
            }
        )

    exports_dir = REPO_ROOT / "exports"
    reports_dir = REPO_ROOT / "reports" / "generated"
    exports_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = exports_dir / "mean_reversion_redesign_runs.csv"
    report_path = reports_dir / "mean_reversion_redesign_report.md"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    report_path.write_text(render_report(rows, args.symbol, args.timeframe, run_mode, start, end), encoding="utf-8")

    print("Completed mean-reversion redesign comparison")
    print(f"Run mode: {run_mode}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Backtest window: {start} -> {end}")
    for row in rows:
        print(
            f"{row['label']} trades={row['trade_count']} gross={row['avg_gross_pnl_per_trade']:.2f} "
            f"net={row['avg_net_pnl_per_trade']:.2f} pf={row['profit_factor']:.2f} "
            f"max_dd={row['max_drawdown']:.2f} avg_cost={row['avg_explicit_cost_per_trade']:.2f}"
        )
    print(f"Report: {report_path}")
    print(f"Runs CSV: {csv_path}")


if __name__ == "__main__":
    main()
