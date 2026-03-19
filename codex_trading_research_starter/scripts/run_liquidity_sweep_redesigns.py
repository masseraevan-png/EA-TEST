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
from research_pipeline.interfaces import StrategyContext
from research_pipeline.strategies.price_action import LiquiditySweepReversalStrategy


def summarize_variant(
    runner: BacktestRunner,
    strategy: LiquiditySweepReversalStrategy,
    parameters: dict[str, object],
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
) -> dict[str, object]:
    artifacts = runner.run(
        strategy=strategy,
        parameters=parameters,
        symbols=[symbol],
        timeframe=timeframe,
        start=start,
        end=end,
    )
    trades = artifacts.trades.copy()
    if trades.empty:
        return {
            "trade_count": 0,
            "avg_hold_hours": 0.0,
            "avg_stop_distance_pips": 0.0,
            "avg_position_size": 0.0,
            "avg_gross_pnl_per_trade": 0.0,
            "avg_net_pnl_per_trade": 0.0,
            "avg_spread_cost_per_trade": 0.0,
            "avg_slippage_cost_per_trade": 0.0,
            "avg_commission_cost_per_trade": 0.0,
            "avg_explicit_cost_per_trade": 0.0,
            "win_rate": 0.0,
            "avg_winner": 0.0,
            "avg_loser": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
        }

    dataset = runner.data_loader.load_symbol(symbol, timeframe)
    bars = dataset.bars.copy()
    bars["timestamp"] = pd.to_datetime(bars["timestamp"])
    bars = bars[(bars["timestamp"] >= pd.Timestamp(start)) & (bars["timestamp"] <= pd.Timestamp(end))].reset_index(drop=True)
    signals = strategy.generate_signals(
        bars,
        StrategyContext(
            symbol=symbol,
            timeframe=timeframe,
            parameters=parameters,
            session_windows=runner.config.raw["sessions"]["definitions"],
        ),
    )
    stop_distance_lookup = {
        pd.Timestamp(signal.timestamp): abs(signal.entry_price - signal.stop_price) / 0.0001 for signal in signals
    }

    holding_hours = (
        pd.to_datetime(trades["exit_time"]) - pd.to_datetime(trades["entry_time"])
    ).dt.total_seconds() / 3600.0
    winners = trades.loc[trades["pnl"] > 0, "pnl"]
    losers = trades.loc[trades["pnl"] < 0, "pnl"]
    explicit_cost = trades["spread_cost_usd"] + trades["slippage_cost_usd"] + trades["commission_cost_usd"]

    return {
        "trade_count": int(len(trades)),
        "avg_hold_hours": float(holding_hours.mean()),
        "avg_stop_distance_pips": float(trades["entry_time"].map(stop_distance_lookup).mean()),
        "avg_position_size": float(trades["position_size"].mean()),
        "avg_gross_pnl_per_trade": float(trades["gross_pnl_usd"].mean()),
        "avg_net_pnl_per_trade": float(trades["pnl"].mean()),
        "avg_spread_cost_per_trade": float(trades["spread_cost_usd"].mean()),
        "avg_slippage_cost_per_trade": float(trades["slippage_cost_usd"].mean()),
        "avg_commission_cost_per_trade": float(trades["commission_cost_usd"].mean()),
        "avg_explicit_cost_per_trade": float(explicit_cost.mean()),
        "win_rate": float((trades["pnl"] > 0).mean()),
        "avg_winner": float(winners.mean()) if not winners.empty else 0.0,
        "avg_loser": float(losers.mean()) if not losers.empty else 0.0,
        "profit_factor": float(artifacts.metrics.profit_factor),
        "max_drawdown": float(artifacts.metrics.max_drawdown),
    }


def render_report(
    baseline_rows: list[dict[str, object]],
    redesign_rows: list[dict[str, object]],
    proposals: list[tuple[str, str]],
    symbol: str,
    timeframe: str,
    run_mode: str,
    start: str,
    end: str,
) -> str:
    proposal_lines = "\n".join(f"- **{name}**: {description}" for name, description in proposals)
    baseline_lines = "\n".join(
        f"| {row['label']} | {row['trade_count']} | {row['avg_hold_hours']:.2f} | {row['avg_stop_distance_pips']:.2f} | "
        f"{row['avg_position_size']:.2f} | {row['avg_gross_pnl_per_trade']:.2f} | {row['avg_net_pnl_per_trade']:.2f} | "
        f"{row['avg_spread_cost_per_trade']:.2f}/{row['avg_slippage_cost_per_trade']:.2f}/{row['avg_commission_cost_per_trade']:.2f} | "
        f"{row['win_rate']:.2%} | {row['avg_winner']:.2f} | {row['avg_loser']:.2f} |"
        for row in baseline_rows
    )
    redesign_lines = "\n".join(
        f"| {row['label']} | {row['trade_count']} | {row['avg_gross_pnl_per_trade']:.2f} | {row['avg_net_pnl_per_trade']:.2f} | "
        f"{row['profit_factor']:.2f} | {row['max_drawdown']:.2f} | {row['avg_explicit_cost_per_trade']:.2f} |"
        for row in redesign_rows
    )
    return f"""# Liquidity Sweep Reversal Redesign Report

## 1. Scope
- Symbol: {symbol}
- Timeframe: {timeframe}
- Run mode: {run_mode}
- Bounded backtest window: {start} to {end}
- Active candidate family: liquidity_sweep_reversal / redesign_fast_rejection only
- Deprioritized: redesign_deep_reclaim and prior breakout/mean-reversion families

## 2. Baseline post-mortem
| Variant | Trades | Avg hold (hrs) | Avg stop (pips) | Avg size (lots) | Gross PnL/trade | Net PnL/trade | Spread/Slip/Comm per trade | Win rate | Avg winner | Avg loser |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{baseline_lines}

## 3. Proposed redesigns
{proposal_lines}

## 4. Implemented bounded test results
| Variant | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Avg explicit cost/trade |
|---|---:|---:|---:|---:|---:|---:|
{redesign_lines}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a compact redesign cycle for liquidity_sweep_reversal.")
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
    strategy = LiquiditySweepReversalStrategy()

    baseline_variants = [
        ("baseline_param_0", strategy.parameter_grid()[0]),
        ("baseline_param_1", strategy.parameter_grid()[1]),
    ]
    redesign_variants = [
        (
            "redesign_fast_rejection_base",
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
        (
            "redesign_fast_rejection_reentry_relief",
            {
                "min_sweep_atr": 0.18,
                "min_reentry_fraction": 0.22,
                "min_wick_fraction": 0.55,
                "min_body_fraction": 0.20,
                "max_close_in_range": 0.43,
                "min_close_in_range": 0.57,
                "min_asia_range_atr": 1.20,
                "allowed_hours": [7, 8, 9, 10, 13, 14],
                "stop_atr": 1.30,
                "target_atr": 2.80,
                "timeout_bars": 10,
                "direction": "both",
            },
        ),
        (
            "redesign_fast_rejection_hour_extension",
            {
                "min_sweep_atr": 0.18,
                "min_reentry_fraction": 0.25,
                "min_wick_fraction": 0.55,
                "min_body_fraction": 0.20,
                "max_close_in_range": 0.40,
                "min_close_in_range": 0.60,
                "min_asia_range_atr": 1.20,
                "allowed_hours": [7, 8, 9, 10, 11, 13, 14],
                "stop_atr": 1.30,
                "target_atr": 2.80,
                "timeout_bars": 10,
                "direction": "both",
            },
        ),
        (
            "redesign_fast_rejection_sweep_relief",
            {
                "min_sweep_atr": 0.16,
                "min_reentry_fraction": 0.25,
                "min_wick_fraction": 0.52,
                "min_body_fraction": 0.18,
                "max_close_in_range": 0.42,
                "min_close_in_range": 0.58,
                "min_asia_range_atr": 1.15,
                "allowed_hours": [7, 8, 9, 10, 13, 14],
                "stop_atr": 1.25,
                "target_atr": 2.60,
                "timeout_bars": 10,
                "direction": "both",
            },
        ),
    ]
    proposals = [
        (
            "fast_rejection_base",
            "Current candidate: sharp wick-led rejections during liquid hours, meaningful reclaim body, and quick exits to avoid paying costs on weak follow-through.",
        ),
        (
            "fast_rejection_reentry_relief",
            "Loosen only the reclaim-depth thresholds slightly to admit bars that still reject decisively but do not close quite as deep inside the range.",
        ),
        (
            "fast_rejection_hour_extension",
            "Keep the base pattern unchanged but add the 11:00 hour to test whether one extra liquid hour can add modest frequency without opening the floodgates.",
        ),
        (
            "fast_rejection_sweep_relief",
            "Slightly reduce the minimum sweep and wick/body strictness while keeping the same rejection family and quick-exit structure.",
        ),
    ]

    baseline_rows = []
    for label, parameters in baseline_variants:
        row = summarize_variant(runner, strategy, parameters, args.symbol, args.timeframe, start, end)
        row["label"] = label
        row["parameters"] = parameters
        baseline_rows.append(row)

    redesign_rows = []
    for label, parameters in redesign_variants:
        row = summarize_variant(runner, strategy, parameters, args.symbol, args.timeframe, start, end)
        row["label"] = label
        row["parameters"] = parameters
        redesign_rows.append(row)

    exports_dir = REPO_ROOT / "exports"
    reports_dir = REPO_ROOT / "reports" / "generated"
    exports_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    baseline_csv_path = exports_dir / "liquidity_sweep_baseline_postmortem.csv"
    redesign_csv_path = exports_dir / "liquidity_sweep_redesign_runs.csv"
    report_path = reports_dir / "liquidity_sweep_redesign_report.md"

    pd.DataFrame(baseline_rows).to_csv(baseline_csv_path, index=False)
    pd.DataFrame(redesign_rows).to_csv(redesign_csv_path, index=False)
    report_path.write_text(
        render_report(baseline_rows, redesign_rows, proposals, args.symbol, args.timeframe, run_mode, start, end),
        encoding="utf-8",
    )

    print("Completed liquidity sweep redesign comparison")
    print(f"Run mode: {run_mode}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Backtest window: {start} -> {end}")
    for row in baseline_rows + redesign_rows:
        print(
            f"{row['label']} trades={row['trade_count']} gross={row['avg_gross_pnl_per_trade']:.2f} "
            f"net={row['avg_net_pnl_per_trade']:.2f} pf={row['profit_factor']:.2f} "
            f"max_dd={row['max_drawdown']:.2f} avg_cost={row['avg_explicit_cost_per_trade']:.2f}"
        )
    print(f"Baseline CSV: {baseline_csv_path}")
    print(f"Redesign CSV: {redesign_csv_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
