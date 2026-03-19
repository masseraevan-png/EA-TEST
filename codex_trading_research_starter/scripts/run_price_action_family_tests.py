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
from research_pipeline.strategies.price_action import LiquiditySweepReversalStrategy, OpeningDrivePullbackStrategy


def render_report(rows: list[dict[str, object]], proposals: list[tuple[str, str]], symbol: str, timeframe: str, run_mode: str, start: str, end: str) -> str:
    proposal_lines = "\n".join(f"- **{name}**: {description}" for name, description in proposals)
    result_lines = "\n".join(
        f"| {row['label']} | {row['trade_count']} | {row['avg_gross_pnl_per_trade']:.2f} | "
        f"{row['avg_net_pnl_per_trade']:.2f} | {row['profit_factor']:.2f} | "
        f"{row['max_drawdown']:.2f} | {row['avg_explicit_cost_per_trade']:.2f} |"
        for row in rows
    )
    return f"""# Price-Action Family Report

## 1. Scope
- Symbol: {symbol}
- Timeframe: {timeframe}
- Run mode: {run_mode}
- Bounded backtest window: {start} to {end}
- Objective: test lower-frequency, more price-action/liquidity-focused alternatives to the prior mean-reversion family.

## 2. Proposed next families
{proposal_lines}

## 3. Tested implementations
| Variant | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|
{result_lines}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run compact bounded tests for new price-action strategy families.")
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

    proposals = [
        (
            "liquidity_sweep_failed_break",
            "Fade London/New York sweeps of the Asian session extreme after a reclaim back inside the range.",
        ),
        (
            "opening_drive_pullback_continuation",
            "Trade only strong opening displacement breaks that pull back shallowly and then resume in the impulse direction.",
        ),
        (
            "compression_breakout_retest",
            "Wait for a tight intraday coil near session boundary, then trade only breakout-retest continuation rather than first-touch breakout.",
        ),
        (
            "range_reclaim_after_stop_run",
            "Trade reclaims of prior day high/low after a stop run fails and price closes back through the breached level.",
        ),
    ]

    variants = [
        ("liquidity_sweep_reversal_param_0", LiquiditySweepReversalStrategy(), LiquiditySweepReversalStrategy().parameter_grid()[0]),
        ("liquidity_sweep_reversal_param_1", LiquiditySweepReversalStrategy(), LiquiditySweepReversalStrategy().parameter_grid()[1]),
        ("opening_drive_pullback_param_0", OpeningDrivePullbackStrategy(), OpeningDrivePullbackStrategy().parameter_grid()[0]),
        ("opening_drive_pullback_param_1", OpeningDrivePullbackStrategy(), OpeningDrivePullbackStrategy().parameter_grid()[1]),
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
        total_cost = trades["spread_cost_usd"] + trades["slippage_cost_usd"] + trades["commission_cost_usd"] if not trades.empty else pd.Series(dtype=float)
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

    csv_path = exports_dir / "price_action_family_runs.csv"
    best_path = exports_dir / "price_action_family_best.csv"
    report_path = reports_dir / "price_action_family_report.md"
    runs = pd.DataFrame(rows)
    best = (
        runs.sort_values(by=["avg_net_pnl_per_trade", "profit_factor", "trade_count"], ascending=[False, False, False])
        .groupby("strategy_name", as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    runs.to_csv(csv_path, index=False)
    best.to_csv(best_path, index=False)
    report_path.write_text(render_report(rows, proposals, args.symbol, args.timeframe, run_mode, start, end), encoding="utf-8")

    print("Completed price-action family comparison")
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
    print(f"Best CSV: {best_path}")


if __name__ == "__main__":
    main()
