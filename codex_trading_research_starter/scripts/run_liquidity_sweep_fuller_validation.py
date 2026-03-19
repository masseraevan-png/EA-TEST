from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from research_pipeline.backtest import BacktestArtifacts, BacktestRunner, ExecutionOverrides
from research_pipeline.config import load_config
from research_pipeline.evaluation import StressTester, combine_artifacts
from research_pipeline.metrics import by_year, compute_metrics, monthly_returns
from research_pipeline.strategies.price_action import LiquiditySweepReversalStrategy, _allowed_hours, _base_frame
from research_pipeline.walkforward import WalkForwardSummary, WalkForwardWindow


FIXED_VARIANTS: list[tuple[str, dict[str, object]]] = [
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
]
MAX_WALKFORWARD_WINDOWS = 4


def summarize_artifacts(artifacts: BacktestArtifacts) -> dict[str, float | int]:
    trades = artifacts.trades
    explicit_cost = pd.Series(dtype=float)
    if not trades.empty:
        explicit_cost = trades["spread_cost_usd"] + trades["slippage_cost_usd"] + trades["commission_cost_usd"]
    return {
        "trade_count": int(artifacts.metrics.total_trades),
        "gross_pnl_per_trade": float(trades["gross_pnl_usd"].mean()) if not trades.empty else 0.0,
        "net_pnl_per_trade": float(artifacts.metrics.expectancy_per_trade),
        "profit_factor": float(artifacts.metrics.profit_factor),
        "max_drawdown": float(artifacts.metrics.max_drawdown),
        "return_to_max_drawdown": float(artifacts.metrics.return_to_max_drawdown),
        "avg_explicit_cost_per_trade": float(explicit_cost.mean()) if not trades.empty else 0.0,
        "total_return": float(artifacts.metrics.total_return),
    }


def generate_signals_from_precomputed_frame(frame: pd.DataFrame, parameters: dict[str, object]) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    direction = str(parameters["direction"])
    allowed_hours = _allowed_hours(parameters)
    for idx in range(20, len(frame) - 1):
        row = frame.iloc[idx]
        if row["hour"] not in allowed_hours or pd.isna(row["atr"]) or pd.isna(row["asia_high"]) or row["bar_range"] <= 0:
            continue
        min_sweep = float(parameters["min_sweep_atr"]) * float(row["atr"])
        min_asia_range_atr = float(parameters.get("min_asia_range_atr", 0.0))
        if row["asia_range"] <= 0 or row["asia_range"] < min_asia_range_atr * float(row["atr"]):
            continue
        close_in_range = (row["close"] - row["low"]) / row["bar_range"]
        upper_wick = (row["high"] - max(row["open"], row["close"])) / row["bar_range"]
        lower_wick = (min(row["open"], row["close"]) - row["low"]) / row["bar_range"]
        body_fraction = abs(row["close"] - row["open"]) / row["bar_range"]
        entry = float(frame.iloc[idx + 1]["open"])
        atr = float(row["atr"])

        swept_above = row["high"] >= row["asia_high"] + min_sweep and row["close"] < row["asia_high"] - float(parameters["min_reentry_fraction"]) * row["asia_range"]
        swept_below = row["low"] <= row["asia_low"] - min_sweep and row["close"] > row["asia_low"] + float(parameters["min_reentry_fraction"]) * row["asia_range"]

        if (
            swept_above
            and upper_wick >= float(parameters["min_wick_fraction"])
            and body_fraction >= float(parameters.get("min_body_fraction", 0.0))
            and close_in_range <= float(parameters.get("max_close_in_range", 1.0))
            and direction in {"short_only", "both"}
        ):
            signals.append(
                {
                    "timestamp": frame.iloc[idx + 1]["timestamp"],
                    "side": -1,
                    "entry_price": entry,
                    "stop_price": float(entry + float(parameters["stop_atr"]) * atr),
                    "target_price": float(entry - float(parameters["target_atr"]) * atr),
                    "timeout_bars": int(parameters["timeout_bars"]),
                    "metadata": {"reason": "asia_high_sweep_reversal_short"},
                }
            )
        elif (
            swept_below
            and lower_wick >= float(parameters["min_wick_fraction"])
            and body_fraction >= float(parameters.get("min_body_fraction", 0.0))
            and close_in_range >= float(parameters.get("min_close_in_range", 0.0))
            and direction in {"long_only", "both"}
        ):
            signals.append(
                {
                    "timestamp": frame.iloc[idx + 1]["timestamp"],
                    "side": 1,
                    "entry_price": entry,
                    "stop_price": float(entry - float(parameters["stop_atr"]) * atr),
                    "target_price": float(entry + float(parameters["target_atr"]) * atr),
                    "timeout_bars": int(parameters["timeout_bars"]),
                    "metadata": {"reason": "asia_low_sweep_reversal_long"},
                }
            )
    return signals


def run_cached_artifacts(
    runner: BacktestRunner,
    parameters: dict[str, object],
    symbol: str,
    frame: pd.DataFrame,
    start: str,
    end: str,
    data_source: str,
    quality_summary: dict[str, object],
    cost_multipliers: tuple[float, float, float] = (1.0, 1.0, 1.0),
    execution_overrides: ExecutionOverrides | None = None,
) -> BacktestArtifacts:
    actual_overrides = execution_overrides or ExecutionOverrides()
    bars = frame[(frame["timestamp"] >= pd.Timestamp(start)) & (frame["timestamp"] <= pd.Timestamp(end))].reset_index(drop=True)
    from research_pipeline.interfaces import SignalEvent
    signals = [SignalEvent(**signal) for signal in generate_signals_from_precomputed_frame(bars, parameters)]
    requests = [(symbol, bars, signal) for signal in signals]
    trades = runner._simulate_signals(requests, cost_multipliers, actual_overrides)
    equity_curve = runner._build_equity_curve(trades)
    metrics = compute_metrics(trades, equity_curve)
    return BacktestArtifacts(
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
        monthly_returns=monthly_returns(trades),
        yearly_results=by_year(trades),
        data_sources={symbol: data_source},
        data_quality={symbol: quality_summary},
    )


def run_fixed_walkforward(
    runner: BacktestRunner,
    parameters: dict[str, object],
    symbol: str,
    split: dict[str, str],
    config_raw: dict[str, object],
    frame: pd.DataFrame,
    data_source: str,
    quality_summary: dict[str, object],
) -> tuple[list[WalkForwardWindow], WalkForwardSummary]:
    from dateutil.relativedelta import relativedelta

    current = pd.Timestamp(split["train_start"])
    final_end = pd.Timestamp(split["test_end"])
    wf_cfg = config_raw["walk_forward"]
    train_months = int(wf_cfg["train_months"])
    validation_months = int(wf_cfg["validation_months"])
    test_months = int(wf_cfg["test_months"])
    step_months = int(wf_cfg["step_months"])
    min_pf = float(config_raw["filters"]["min_oos_profit_factor"])

    windows: list[WalkForwardWindow] = []
    while True:
        train_start = current
        train_end = train_start + relativedelta(months=train_months) - relativedelta(days=1)
        validation_start = train_end + relativedelta(days=1)
        validation_end = validation_start + relativedelta(months=validation_months) - relativedelta(days=1)
        test_start = validation_end + relativedelta(days=1)
        test_end = test_start + relativedelta(months=test_months) - relativedelta(days=1)
        if test_end > final_end:
            break

        train = run_cached_artifacts(runner, parameters, symbol, frame, str(train_start.date()), str(train_end.date()), data_source, quality_summary)
        validation = run_cached_artifacts(runner, parameters, symbol, frame, str(validation_start.date()), str(validation_end.date()), data_source, quality_summary)
        test = run_cached_artifacts(runner, parameters, symbol, frame, str(test_start.date()), str(test_end.date()), data_source, quality_summary)
        passed = test.metrics.total_return > 0 and test.metrics.profit_factor >= min_pf
        windows.append(
            WalkForwardWindow(
                train_start=str(train_start.date()),
                train_end=str(train_end.date()),
                validation_start=str(validation_start.date()),
                validation_end=str(validation_end.date()),
                test_start=str(test_start.date()),
                test_end=str(test_end.date()),
                selected_parameters=parameters,
                train_return=train.metrics.total_return,
                train_profit_factor=train.metrics.profit_factor,
                train_trades=train.metrics.total_trades,
                validation_return=validation.metrics.total_return,
                validation_profit_factor=validation.metrics.profit_factor,
                validation_trades=validation.metrics.total_trades,
                test_return=test.metrics.total_return,
                test_profit_factor=test.metrics.profit_factor,
                test_trades=test.metrics.total_trades,
                passed=passed,
            )
        )
        current = current + relativedelta(months=step_months)
        if len(windows) >= MAX_WALKFORWARD_WINDOWS:
            break

    if not windows:
        return [], WalkForwardSummary(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    test_returns = pd.Series([window.test_return for window in windows], dtype=float)
    test_pf = pd.Series([window.test_profit_factor for window in windows], dtype=float)
    passed_windows = sum(1 for window in windows if window.passed)
    summary = WalkForwardSummary(
        total_windows=len(windows),
        passed_windows=passed_windows,
        pass_ratio=passed_windows / len(windows),
        average_test_return=float(test_returns.mean()),
        average_test_profit_factor=float(test_pf.mean()),
        best_window_return=float(test_returns.max()),
        worst_window_return=float(test_returns.min()),
        test_return_std=float(test_returns.std(ddof=0)),
        test_profit_factor_std=float(test_pf.std(ddof=0)),
    )
    return windows, summary


def render_report(
    symbol: str,
    timeframe: str,
    run_mode: str,
    split_rows: list[dict[str, object]],
    aggregate_rows: list[dict[str, object]],
    walkforward_rows: list[dict[str, object]],
    variant_summaries: list[dict[str, object]],
    conclusion_lines: list[str],
) -> str:
    split_table = "\n".join(
        f"| {row['variant']} | {row['window']} | {row['start']} | {row['end']} | {row['trade_count']} | "
        f"{row['gross_pnl_per_trade']:.2f} | {row['net_pnl_per_trade']:.2f} | {row['profit_factor']:.2f} | "
        f"{row['max_drawdown']:.2f} | {row['return_to_max_drawdown']:.2f} | {row['avg_explicit_cost_per_trade']:.2f} |"
        for row in split_rows
    )
    aggregate_table = "\n".join(
        f"| {row['variant']} | {row['window']} | {row['trade_count']} | {row['gross_pnl_per_trade']:.2f} | "
        f"{row['net_pnl_per_trade']:.2f} | {row['profit_factor']:.2f} | {row['max_drawdown']:.2f} | "
        f"{row['return_to_max_drawdown']:.2f} | {row['avg_explicit_cost_per_trade']:.2f} |"
        for row in aggregate_rows
    )
    walkforward_table = "\n".join(
        f"| {row['variant']} | {row['test_start']} | {row['test_end']} | {row['train_trades']} | {row['validation_trades']} | {row['test_trades']} | "
        f"{row['test_return']:.2f} | {row['test_profit_factor']:.2f} | {row['passed']} |"
        for row in walkforward_rows
    )
    summary_table = "\n".join(
        f"| {row['variant']} | {row['total_trades']} | {row['train_trades']} / {row['validation_trades']} / {row['test_trades']} / {row['holdout_trades']} | "
        f"{row['gross_pnl_per_trade']:.2f} | {row['net_pnl_per_trade']:.2f} | {row['profit_factor']:.2f} | {row['max_drawdown']:.2f} | "
        f"{row['return_to_max_drawdown']:.2f} | {row['avg_explicit_cost_per_trade']:.2f} | {row['walkforward_pass_rate']:.2%} | {row['stress_pass_rate']:.2%} | {row['classification']} |"
        for row in variant_summaries
    )
    conclusions = "\n".join(f"- {line}" for line in conclusion_lines)
    return f"""# Fuller Validation Report: Liquidity Sweep Reversal

## Scope
- Symbol: {symbol}
- Timeframe: {timeframe}
- Run mode: {run_mode}
- Active variants only: `redesign_fast_rejection_base`, `redesign_fast_rejection_reentry_relief`
- Deprioritized and excluded from execution: `redesign_deep_reclaim`, `redesign_fast_rejection_hour_extension`, `redesign_fast_rejection_sweep_relief`, and all prior breakout / mean-reversion families.
- Research policy: fixed-logic evaluation only, no broad family search, no redesign iteration inside this run.

## Window results
| Variant | Window | Start | End | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Return / Max DD | Avg explicit cost/trade |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
{split_table}

## Aggregate slices
| Variant | Aggregate slice | Trades | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Return / Max DD | Avg explicit cost/trade |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{aggregate_table}

## Fixed-parameter walk-forward windows
| Variant | Test start | Test end | Train trades | Validation trades | Test trades | Test return | Test PF | Passed |
|---|---|---|---:|---:|---:|---:|---:|---:|
{walkforward_table}

## Variant scorecard
| Variant | Total trades | Trades by split (train / validation / test / holdout) | Gross PnL/trade | Net PnL/trade | Profit factor | Max drawdown | Return / Max DD | Avg explicit cost/trade | Walk-forward pass rate | Stress-test pass rate | Classification |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{summary_table}

## Conclusions
{conclusions}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fuller fixed-logic validation for the selected liquidity sweep redesigns.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--mode", choices=["demo_mode", "real_research_mode"], default="real_research_mode")
    parser.add_argument("--config", default=str(REPO_ROOT / "configs" / "base_config.yaml"))
    args = parser.parse_args()

    config = load_config(Path(args.config))
    run_mode = config.resolve_run_mode(args.mode)
    split = config.split
    runner = BacktestRunner(repo_root=REPO_ROOT, config=config, run_mode=run_mode)
    stress_tester = StressTester(runner, config)
    dataset = runner.data_loader.load_symbol(args.symbol, args.timeframe)
    all_bars = dataset.bars.copy()
    all_bars["timestamp"] = pd.to_datetime(all_bars["timestamp"])
    precomputed_frame = _base_frame(all_bars)
    data_source = dataset.source
    quality_summary = dataset.quality_summary

    split_defs = [
        ("train", split["train_start"], split["train_end"]),
        ("validation", split["validation_start"], split["validation_end"]),
        ("test", split["test_start"], split["test_end"]),
        ("holdout", split["holdout_start"], split["holdout_end"]),
    ]

    split_rows: list[dict[str, object]] = []
    aggregate_rows: list[dict[str, object]] = []
    walkforward_rows: list[dict[str, object]] = []
    variant_summaries: list[dict[str, object]] = []
    conclusion_lines: list[str] = []
    stress_tables: list[pd.DataFrame] = []

    for variant_name, parameters in FIXED_VARIANTS:
        artifacts_by_window: dict[str, BacktestArtifacts] = {}
        for window_name, start, end in split_defs:
            artifacts = run_cached_artifacts(
                runner,
                parameters,
                args.symbol,
                precomputed_frame,
                start,
                end,
                data_source,
                quality_summary,
            )
            artifacts_by_window[window_name] = artifacts
            row = summarize_artifacts(artifacts)
            row.update({
                "variant": variant_name,
                "window": window_name,
                "start": start,
                "end": end,
            })
            split_rows.append(row)

        combined_oos = combine_artifacts([artifacts_by_window["validation"], artifacts_by_window["test"]])
        full_sample = combine_artifacts([
            artifacts_by_window["train"],
            artifacts_by_window["validation"],
            artifacts_by_window["test"],
            artifacts_by_window["holdout"],
        ])
        oos_plus_holdout = combine_artifacts([
            artifacts_by_window["validation"],
            artifacts_by_window["test"],
            artifacts_by_window["holdout"],
        ])
        for window_name, artifacts in [
            ("combined_oos", combined_oos),
            ("oos_plus_holdout", oos_plus_holdout),
            ("full_sample", full_sample),
        ]:
            row = summarize_artifacts(artifacts)
            row.update({"variant": variant_name, "window": window_name})
            aggregate_rows.append(row)

        wf_windows, wf_summary = run_fixed_walkforward(
            runner=runner,
            parameters=parameters,
            symbol=args.symbol,
            split=split,
            config_raw=config.raw,
            frame=precomputed_frame,
            data_source=data_source,
            quality_summary=quality_summary,
        )
        for row in wf_windows:
            row_dict = asdict(row)
            row_dict["variant"] = variant_name
            walkforward_rows.append(row_dict)

        stress_results, stress_summary = stress_tester.run(
            LiquiditySweepReversalStrategy(),
            parameters,
            [args.symbol],
            args.timeframe,
            split["validation_start"],
            split["test_end"],
        )
        stress_tables.append(stress_results.assign(variant=variant_name))

        full_summary = summarize_artifacts(full_sample)
        variant_summary = {
            "variant": variant_name,
            "total_trades": int(full_summary["trade_count"]),
            "train_trades": int(artifacts_by_window["train"].metrics.total_trades),
            "validation_trades": int(artifacts_by_window["validation"].metrics.total_trades),
            "test_trades": int(artifacts_by_window["test"].metrics.total_trades),
            "holdout_trades": int(artifacts_by_window["holdout"].metrics.total_trades),
            "gross_pnl_per_trade": float(full_summary["gross_pnl_per_trade"]),
            "net_pnl_per_trade": float(full_summary["net_pnl_per_trade"]),
            "profit_factor": float(full_summary["profit_factor"]),
            "max_drawdown": float(full_summary["max_drawdown"]),
            "return_to_max_drawdown": float(full_summary["return_to_max_drawdown"]),
            "avg_explicit_cost_per_trade": float(full_summary["avg_explicit_cost_per_trade"]),
            "walkforward_pass_rate": float(wf_summary.pass_ratio),
            "stress_pass_rate": float(stress_summary["pass_rate"]),
            "classification": (
                "Survivor candidate"
                if combined_oos.metrics.total_trades >= config.raw["filters"]["min_oos_trades"]
                and combined_oos.metrics.profit_factor >= config.raw["filters"]["min_oos_profit_factor"]
                and combined_oos.metrics.total_return > 0
                and combined_oos.metrics.return_to_max_drawdown >= config.raw["filters"]["min_oos_return_to_max_dd"]
                and wf_summary.total_windows >= config.raw["walk_forward"]["min_windows"]
                and wf_summary.pass_ratio >= 0.5
                and float(stress_summary["pass_rate"]) >= 0.5
                and not (
                    artifacts_by_window["holdout"].metrics.total_trades >= 20
                    and (
                        artifacts_by_window["holdout"].metrics.total_return < 0
                        or artifacts_by_window["holdout"].metrics.profit_factor < 0.95
                        or artifacts_by_window["holdout"].metrics.return_to_max_drawdown < 0.50
                    )
                )
                else "Rejected"
            ),
        }
        variant_summaries.append(variant_summary)

        holdout = artifacts_by_window["holdout"].metrics
        base_message = (
            f"{variant_name}: combined OOS trades={combined_oos.metrics.total_trades}, PF={combined_oos.metrics.profit_factor:.2f}, "
            f"return/maxDD={combined_oos.metrics.return_to_max_drawdown:.2f}, holdout trades={holdout.total_trades}, "
            f"holdout PF={holdout.profit_factor:.2f}, walk-forward pass rate={wf_summary.pass_ratio:.2%}, stress pass rate={float(stress_summary['pass_rate']):.2%}."
        )
        conclusion_lines.append(base_message)

    base_summary = next(row for row in variant_summaries if row["variant"] == "redesign_fast_rejection_base")
    relief_summary = next(row for row in variant_summaries if row["variant"] == "redesign_fast_rejection_reentry_relief")
    conclusion_lines.append(
        "Base candidate verdict: survives fuller validation only if its combined out-of-sample metrics, walk-forward pass rate, stress pass rate, and holdout sanity all stay above the stated thresholds; otherwise treat the earlier signal as a small-sample illusion."
        if base_summary["classification"] != "Rejected"
        else "Base candidate verdict: rejected under the fuller fixed-logic pipeline, so the earlier promise does not survive a stricter evidence bar."
    )
    conclusion_lines.append(
        "Reentry relief verdict: keep as a shadow arm only if it clearly improves evidence quality versus the base without weakening holdout or stress behavior; otherwise drop it."
        if relief_summary["classification"] != "Rejected"
        else "Reentry relief verdict: drop it, because the fuller pipeline does not justify keeping it as an active shadow arm."
    )
    if all(row["classification"] == "Rejected" for row in variant_summaries):
        conclusion_lines.append("Active-candidate verdict: neither variant deserves to remain active after this fuller validation run.")
    else:
        survivors = ", ".join(row["variant"] for row in variant_summaries if row["classification"] != "Rejected")
        conclusion_lines.append(f"Active-candidate verdict: keep only {survivors} active, and keep the logic frozen until fresh evidence justifies another redesign cycle.")

    exports_dir = REPO_ROOT / "exports"
    reports_dir = REPO_ROOT / "reports" / "generated"
    exports_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    split_df = pd.DataFrame(split_rows)
    aggregate_df = pd.DataFrame(aggregate_rows)
    walkforward_df = pd.DataFrame(walkforward_rows)
    summary_df = pd.DataFrame(variant_summaries)
    stress_df = pd.concat(stress_tables, ignore_index=True)

    split_df.to_csv(exports_dir / "liquidity_sweep_fuller_validation_windows.csv", index=False)
    aggregate_df.to_csv(exports_dir / "liquidity_sweep_fuller_validation_aggregates.csv", index=False)
    walkforward_df.to_csv(exports_dir / "liquidity_sweep_fuller_validation_walkforward.csv", index=False)
    stress_df.to_csv(exports_dir / "liquidity_sweep_fuller_validation_stress.csv", index=False)
    summary_df.to_csv(exports_dir / "liquidity_sweep_fuller_validation_summary.csv", index=False)
    report_path = reports_dir / "liquidity_sweep_fuller_validation_report.md"
    report_path.write_text(
        render_report(
            symbol=args.symbol,
            timeframe=args.timeframe,
            run_mode=run_mode,
            split_rows=split_rows,
            aggregate_rows=aggregate_rows,
            walkforward_rows=walkforward_rows,
            variant_summaries=variant_summaries,
            conclusion_lines=conclusion_lines,
        ),
        encoding="utf-8",
    )

    print("Completed fuller liquidity sweep validation")
    print(f"Report: {report_path}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
