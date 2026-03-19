from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from research_pipeline.backtest import BacktestRunner, ExecutionOverrides
from research_pipeline.config import load_config
from research_pipeline.interfaces import StrategyContext
from research_pipeline.strategies.price_action import LiquiditySweepReversalStrategy


REDESIGN_VARIANTS: list[tuple[str, dict[str, object]]] = [
    (
        "redesign_deep_reclaim",
        {
            "min_sweep_atr": 0.20,
            "min_reentry_fraction": 0.30,
            "min_wick_fraction": 0.50,
            "min_body_fraction": 0.25,
            "max_close_in_range": 0.35,
            "min_close_in_range": 0.65,
            "min_asia_range_atr": 1.50,
            "allowed_hours": [7, 8, 9, 13, 14],
            "stop_atr": 1.20,
            "target_atr": 3.00,
            "timeout_bars": 12,
            "direction": "both",
        },
    ),
    (
        "redesign_fast_rejection",
        {
            "min_sweep_atr": 0.18,
            "min_reentry_fraction": 0.25,
            "min_wick_fraction": 0.55,
            "min_body_fraction": 0.20,
            "max_close_in_range": 0.40,
            "min_close_in_range": 0.60,
            "min_asia_range_atr": 1.20,
            "allowed_hours": [7, 8, 9, 10, 13, 14],
            "stop_atr": 1.30,
            "target_atr": 2.80,
            "timeout_bars": 10,
            "direction": "both",
        },
    ),
]


def summarize_variant_cached(
    runner: BacktestRunner,
    strategy: LiquiditySweepReversalStrategy,
    parameters: dict[str, object],
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    all_bars: pd.DataFrame,
) -> dict[str, object]:
    bars = all_bars[(all_bars["timestamp"] >= pd.Timestamp(start)) & (all_bars["timestamp"] <= pd.Timestamp(end))].reset_index(drop=True)
    signals = strategy.generate_signals(
        bars,
        StrategyContext(
            symbol=symbol,
            timeframe=timeframe,
            parameters=parameters,
            session_windows=runner.config.raw["sessions"]["definitions"],
        ),
    )
    requests = [(symbol, bars, signal) for signal in signals]
    trades = runner._simulate_signals(requests, cost_multipliers=(1.0, 1.0, 1.0), execution_overrides=ExecutionOverrides())
    if trades.empty:
        return {
            "trade_count": 0,
            "avg_gross_pnl_per_trade": 0.0,
            "avg_net_pnl_per_trade": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "avg_explicit_cost_per_trade": 0.0,
        }

    pnl = trades["pnl"]
    equity_curve = 100000.0 + pnl.cumsum()
    running_peak = equity_curve.cummax()
    drawdown = running_peak - equity_curve
    winners = trades.loc[trades["pnl"] > 0, "pnl"].sum()
    losers = abs(trades.loc[trades["pnl"] < 0, "pnl"].sum())
    explicit_cost = trades["spread_cost_usd"] + trades["slippage_cost_usd"] + trades["commission_cost_usd"]

    return {
        "trade_count": int(len(trades)),
        "avg_gross_pnl_per_trade": float(trades["gross_pnl_usd"].mean()),
        "avg_net_pnl_per_trade": float(trades["pnl"].mean()),
        "profit_factor": float(winners / losers) if losers else (float("inf") if winners > 0 else 0.0),
        "max_drawdown": float(drawdown.max()),
        "avg_explicit_cost_per_trade": float(explicit_cost.mean()),
    }


def render_validation_report(
    rows: list[dict[str, object]],
    summary_rows: list[dict[str, object]],
    symbol: str,
    timeframe: str,
    run_mode: str,
) -> str:
    window_lines = "\n".join(
        f"| {row['variant']} | {row['window_label']} | {row['start']} | {row['end']} | {row['trade_count']} | "
        f"{row['avg_gross_pnl_per_trade']:.2f} | {row['avg_net_pnl_per_trade']:.2f} | {row['profit_factor']:.2f} | "
        f"{row['max_drawdown']:.2f} | {row['avg_explicit_cost_per_trade']:.2f} |"
        for row in rows
    )
    summary_lines = "\n".join(
        f"| {row['variant']} | {row['total_trades']} | {row['positive_windows']}/{row['window_count']} | "
        f"{row['mean_net_pnl_per_trade']:.2f} | {row['median_net_pnl_per_trade']:.2f} | {row['mean_profit_factor']:.2f} | "
        f"{row['worst_max_drawdown']:.2f} | {row['mean_explicit_cost_per_trade']:.2f} |"
        for row in summary_rows
    )
    return f"""# Liquidity Sweep Reversal Validation Report

## 1. Scope
- Symbol: {symbol}
- Timeframe: {timeframe}
- Run mode: {run_mode}
- Active candidate family: liquidity_sweep_reversal only
- Validation style: bounded, fixed-logic multi-window check
- Optimization/search policy: no further optimization, no broad parameter search

## 2. Window-by-window results
| Variant | Window | Start | End | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
{window_lines}

## 3. Cross-window summary
| Variant | Total trades | Positive net windows | Mean net PnL/trade | Median net PnL/trade | Mean profit factor | Worst max drawdown | Mean explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|---:|
{summary_lines}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a bounded multi-window validation for liquidity_sweep_reversal redesigns.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--mode", choices=["demo_mode", "real_research_mode"], default="real_research_mode")
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "base_config.yaml"))
    args = parser.parse_args()

    config = load_config(Path(args.config))
    run_mode = config.resolve_run_mode(args.mode)
    windows = [
        ("earlier_in_sample_style", "2022-01-01", "2022-06-30"),
        ("later_out_of_sample_style", "2024-01-01", "2024-06-30"),
        ("recent_holdout_style", "2025-01-01", "2025-06-30"),
    ]

    runner = BacktestRunner(repo_root=REPO_ROOT, config=config, run_mode=run_mode)
    strategy = LiquiditySweepReversalStrategy()
    dataset = runner.data_loader.load_symbol(args.symbol, args.timeframe)
    all_bars = dataset.bars.copy()
    all_bars["timestamp"] = pd.to_datetime(all_bars["timestamp"])

    rows: list[dict[str, object]] = []
    for window_label, start, end in windows:
        for variant, parameters in REDESIGN_VARIANTS:
            row = summarize_variant_cached(runner, strategy, parameters, args.symbol, args.timeframe, start, end, all_bars)
            row.update(
                {
                    "variant": variant,
                    "window_label": window_label,
                    "start": start,
                    "end": end,
                    "parameters": parameters,
                }
            )
            rows.append(row)

    results = pd.DataFrame(rows)
    summary = (
        results.groupby("variant", dropna=False)
        .agg(
            total_trades=("trade_count", "sum"),
            window_count=("window_label", "count"),
            positive_windows=("avg_net_pnl_per_trade", lambda s: int((s > 0).sum())),
            mean_net_pnl_per_trade=("avg_net_pnl_per_trade", "mean"),
            median_net_pnl_per_trade=("avg_net_pnl_per_trade", "median"),
            mean_profit_factor=("profit_factor", "mean"),
            worst_max_drawdown=("max_drawdown", "max"),
            mean_explicit_cost_per_trade=("avg_explicit_cost_per_trade", "mean"),
        )
        .reset_index()
    )

    exports_dir = REPO_ROOT / "exports"
    reports_dir = REPO_ROOT / "reports" / "generated"
    exports_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    results_path = exports_dir / "liquidity_sweep_redesign_validation_windows.csv"
    summary_path = exports_dir / "liquidity_sweep_redesign_validation_summary.csv"
    report_path = reports_dir / "liquidity_sweep_redesign_validation_report.md"

    results.to_csv(results_path, index=False)
    summary.to_csv(summary_path, index=False)
    report_path.write_text(
        render_validation_report(rows, summary.to_dict("records"), args.symbol, args.timeframe, run_mode),
        encoding="utf-8",
    )

    print("Completed bounded liquidity sweep redesign validation")
    print(f"Run mode: {run_mode}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    for row in rows:
        print(
            f"{row['variant']} window={row['window_label']} trades={row['trade_count']} "
            f"gross={row['avg_gross_pnl_per_trade']:.2f} net={row['avg_net_pnl_per_trade']:.2f} "
            f"pf={row['profit_factor']:.2f} max_dd={row['max_drawdown']:.2f} avg_cost={row['avg_explicit_cost_per_trade']:.2f}"
        )
    print(f"Windows CSV: {results_path}")
    print(f"Summary CSV: {summary_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
