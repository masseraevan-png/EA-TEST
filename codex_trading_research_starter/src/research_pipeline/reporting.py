from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import BacktestArtifacts
from .evaluation import StrategyBatchResult, monte_carlo_summary


class ReportWriter:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def write_batch_outputs(
        self,
        batch: StrategyBatchResult,
        walkforward_rows: list[dict[str, Any]],
        strategy_hypothesis: str,
        strategy_description: str,
        timeframe: str,
        symbols: list[str],
        symbol_unit_notes: list[str],
        data_source_notes: list[str],
        data_quality_notes: list[str],
        data_quality_warning_details: list[str],
    ) -> dict[str, Path]:
        reports_dir = self.repo_root / "reports" / "generated"
        exports_dir = self.repo_root / "exports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)
        slug = batch.strategy_name

        batch.test.monthly_returns.to_csv(exports_dir / f"{slug}_monthly_returns.csv", index=False)
        batch.by_symbol_oos.to_csv(exports_dir / f"{slug}_by_symbol_oos.csv", index=False)
        batch.neighborhood.to_csv(exports_dir / f"{slug}_parameter_sensitivity.csv", index=False)
        batch.stress_results.to_csv(exports_dir / f"{slug}_stress_tests.csv", index=False)
        batch.combined_oos.trades.to_csv(exports_dir / f"{slug}_trade_log.csv", index=False)
        batch.combined_oos.equity_curve.to_csv(exports_dir / f"{slug}_equity_curve.csv", index=False)
        pd.DataFrame(walkforward_rows).to_csv(exports_dir / f"{slug}_walkforward.csv", index=False)

        monte_carlo = monte_carlo_summary(batch.combined_oos.trades, 500)
        report_path = reports_dir / f"{slug}_report.md"
        report_path.write_text(
            self._render_report(
                batch,
                walkforward_rows,
                strategy_hypothesis,
                strategy_description,
                timeframe,
                symbols,
                monte_carlo,
                symbol_unit_notes,
                data_source_notes,
                data_quality_notes,
                data_quality_warning_details,
            ),
            encoding="utf-8",
        )
        comparison = pd.DataFrame([
            {
                "strategy_name": batch.strategy_name,
                "classification": batch.classification,
                "oos_return": batch.combined_oos.metrics.total_return,
                "oos_profit_factor": batch.combined_oos.metrics.profit_factor,
                "oos_return_to_max_dd": batch.combined_oos.metrics.return_to_max_drawdown,
                "neighbor_pass_ratio": batch.neighbor_pass_ratio,
            }
        ])
        comparison_path = exports_dir / "strategy_comparison.csv"
        if comparison_path.exists():
            existing = pd.read_csv(comparison_path)
            comparison = pd.concat([existing, comparison], ignore_index=True)
        comparison.drop_duplicates(subset=["strategy_name"], keep="last").to_csv(comparison_path, index=False)
        return {"report": report_path, "comparison": comparison_path}

    def write_smoke_test_outputs(
        self,
        *,
        strategy_name: str,
        run_mode: str,
        timeframe: str,
        symbols: list[str],
        start: str,
        end: str,
        parameters: dict[str, Any],
        artifacts: BacktestArtifacts,
        skipped_steps: list[str],
    ) -> dict[str, Path]:
        reports_dir = self.repo_root / "reports" / "generated"
        exports_dir = self.repo_root / "exports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)
        slug = f"{strategy_name}_smoke_test"

        trade_log_path = exports_dir / f"{slug}_trade_log.csv"
        equity_curve_path = exports_dir / f"{slug}_equity_curve.csv"
        monthly_returns_path = exports_dir / f"{slug}_monthly_returns.csv"
        summary_path = exports_dir / f"{slug}_summary.json"
        report_path = reports_dir / f"{slug}_report.md"

        artifacts.trades.to_csv(trade_log_path, index=False)
        artifacts.equity_curve.to_csv(equity_curve_path, index=False)
        artifacts.monthly_returns.to_csv(monthly_returns_path, index=False)
        summary_payload = {
            "strategy_name": strategy_name,
            "run_mode": run_mode,
            "timeframe": timeframe,
            "symbols": symbols,
            "start": start,
            "end": end,
            "parameters": parameters,
            "data_sources": artifacts.data_sources,
            "data_quality": artifacts.data_quality,
            "metrics": artifacts.metrics.__dict__,
            "skipped_steps": skipped_steps,
        }
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        report_path.write_text(
            self._render_smoke_test_report(
                strategy_name=strategy_name,
                run_mode=run_mode,
                timeframe=timeframe,
                symbols=symbols,
                start=start,
                end=end,
                parameters=parameters,
                artifacts=artifacts,
                skipped_steps=skipped_steps,
            ),
            encoding="utf-8",
        )
        return {
            "report": report_path,
            "trade_log": trade_log_path,
            "equity_curve": equity_curve_path,
            "monthly_returns": monthly_returns_path,
            "summary": summary_path,
        }

    def write_bounded_research_outputs(
        self,
        *,
        symbol: str,
        timeframe: str,
        run_mode: str,
        start: str,
        end: str,
        run_rows: list[dict[str, Any]],
    ) -> dict[str, Path]:
        reports_dir = self.repo_root / "reports" / "generated"
        exports_dir = self.repo_root / "exports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)

        report_path = reports_dir / "bounded_strategy_comparison_report.md"
        runs_path = exports_dir / "bounded_strategy_comparison_runs.csv"
        best_path = exports_dir / "bounded_strategy_comparison_best.csv"

        runs = pd.DataFrame(run_rows)
        best = (
            runs.sort_values(
                by=["return_to_max_drawdown", "profit_factor", "total_return"],
                ascending=[False, False, False],
            )
            .groupby("strategy_name", as_index=False)
            .head(1)
            .reset_index(drop=True)
        )
        runs.to_csv(runs_path, index=False)
        best.to_csv(best_path, index=False)
        report_path.write_text(
            self._render_bounded_research_report(
                symbol=symbol,
                timeframe=timeframe,
                run_mode=run_mode,
                start=start,
                end=end,
                runs=runs,
                best=best,
            ),
            encoding="utf-8",
        )
        return {
            "report": report_path,
            "runs": runs_path,
            "best": best_path,
        }

    def _render_report(self, batch: StrategyBatchResult, walkforward_rows: list[dict[str, Any]], hypothesis: str, description: str, timeframe: str, symbols: list[str], monte_carlo: dict[str, float], symbol_unit_notes: list[str], data_source_notes: list[str], data_quality_notes: list[str], data_quality_warning_details: list[str]) -> str:
        acceptance_lines = "\n".join(
            f"| {row['criterion']} | {row['status']} | {row['comment']} |" for row in batch.acceptance_rows
        )
        symbol_lines = "\n".join(
            f"| {row.symbol} | {row.total_return:.2f} | {row.profit_factor:.2f} | {row.total_trades} | {'Positive' if row.total_return > 0 else 'Weak'} |"
            for row in batch.by_symbol_oos.itertuples()
        ) or "| n/a | 0.00 | 0.00 | 0 | No trades |"
        year_lines = "\n".join(
            f"| {getattr(row, 'year')} | {getattr(row, '_2'):.2f} | {getattr(row, 'profit_factor'):.2f} | n/a | {getattr(row, 'trades')} |"
            for row in batch.combined_oos.yearly_results.itertuples()
        ) or "| n/a | 0.00 | 0.00 | n/a | 0 |"
        wf_lines = "\n".join(
            f"- train={row['train_start']}→{row['train_end']}, validation={row['validation_start']}→{row['validation_end']}, "
            f"test={row['test_start']}→{row['test_end']}, params={row['selected_parameters']}, "
            f"train_pf={row['train_profit_factor']:.2f}, validation_pf={row['validation_profit_factor']:.2f}, "
            f"test_pf={row['test_profit_factor']:.2f}, passed={row['passed']}"
            for row in walkforward_rows
        )
        return f"""# Strategy Report — {batch.strategy_name}

## 1. Research summary
- Final label: {batch.classification}
- Strategy family: {batch.strategy_name}
- Primary symbol(s): {', '.join(symbols)}
- Primary timeframe(s): {timeframe}
- Run mode: {batch.run_mode}
- Short verdict: Conservative phase-1 research result only.

## 2. Hypothesis
- Plain-English intuition: {hypothesis}
- Main assumptions behind the logic: {description}

## 3. Exact rules
- ATR-based stops and targets with next-bar-open entry under conservative bar-based execution.
- No same-bar entry/exit optimism; stop has priority if stop and target are both touched.
- Sizing model: fixed-fractional equity-aware sizing using `initial_equity_usd`, `risk_per_trade`, stop distance, and symbol lot constraints.

## 4. Parameters tested
- Selected parameters: {batch.selected_parameters}

## 5. Data and split integrity
- Train period: 2018-01-01 to 2022-12-31
- Validation period: 2023-01-01 to 2023-12-31
- Test period: 2024-01-01 to 2024-12-31
- Holdout period: 2025-01-01 to 2025-12-31
- Holdout kept untouched during selection?: Yes
- Symbols used: {', '.join(symbols)}
- Data sources:
{chr(10).join(f"  - {note}" for note in data_source_notes)}
- Data-quality audit:
{chr(10).join(f"  - {note}" for note in data_quality_notes)}
- Warning-level same-day gaps:
{chr(10).join(f"  - {note}" for note in data_quality_warning_details) if data_quality_warning_details else "  - None."}

## 6. Cost and execution assumptions
- Explicit symbol-specific costs from `configs/base_config.yaml`
- Conservative execution mode with next-bar-open entries and pessimistic tie-breaking.
- Symbol mechanics:
{chr(10).join(f"  - {note}" for note in symbol_unit_notes)}
- Position sizing assumptions:
  - Equity-aware sizing is applied per trade.
  - Risk budget equals `equity_before * risk_per_trade`.
  - Position size is floored to the configured minimum/step and capped by optional max size.

## 7. In-sample result
- Total return: {batch.train.metrics.total_return:.2f}
- Profit factor: {batch.train.metrics.profit_factor:.2f}
- Max drawdown: {batch.train.metrics.max_drawdown:.2f}
- Return / Max DD: {batch.train.metrics.return_to_max_drawdown:.2f}
- Total trades: {batch.train.metrics.total_trades}

## 8. Validation result
- Total return: {batch.validation.metrics.total_return:.2f}
- Profit factor: {batch.validation.metrics.profit_factor:.2f}
- Trades: {batch.validation.metrics.total_trades}

## 9. Test result
- Total return: {batch.test.metrics.total_return:.2f}
- Profit factor: {batch.test.metrics.profit_factor:.2f}
- Trades: {batch.test.metrics.total_trades}

## 10. Combined out-of-sample result
- Combined OOS return: {batch.combined_oos.metrics.total_return:.2f}
- Combined OOS profit factor: {batch.combined_oos.metrics.profit_factor:.2f}
- Combined OOS max drawdown: {batch.combined_oos.metrics.max_drawdown:.2f}
- Combined OOS Return / Max DD: {batch.combined_oos.metrics.return_to_max_drawdown:.2f}
- Combined OOS expectancy in R: {batch.combined_oos.metrics.expectancy_r:.4f}
- Combined OOS trades: {batch.combined_oos.metrics.total_trades}

## 11. Holdout result
- Total return: {batch.holdout.metrics.total_return:.2f}
- Profit factor: {batch.holdout.metrics.profit_factor:.2f}
- Return / Max DD: {batch.holdout.metrics.return_to_max_drawdown:.2f}
- Trades: {batch.holdout.metrics.total_trades}

## 12. Walk-forward summary
- Total windows: {batch.walkforward_summary['total_windows']}
- Passed windows: {batch.walkforward_summary['passed_windows']}
- Average walk-forward test return: {batch.walkforward_summary['average_test_return']:.2f}
- Average walk-forward test profit factor: {batch.walkforward_summary['average_test_profit_factor']:.2f}
- Best window return: {batch.walkforward_summary['best_window_return']:.2f}
- Worst window return: {batch.walkforward_summary['worst_window_return']:.2f}
- Test return dispersion (std): {batch.walkforward_summary['test_return_std']:.2f}
- Test PF dispersion (std): {batch.walkforward_summary['test_profit_factor_std']:.2f}
{wf_lines}

## 13. Stress tests
- Stress pass rate: {batch.stress_summary['pass_rate']:.2f}
- Average stressed return: {batch.stress_summary['average_return']:.2f}
- Worst stressed return: {batch.stress_summary['worst_return']:.2f}
- Worst stressed profit factor: {batch.stress_summary['worst_profit_factor']:.2f}
- Moderate scenario remained acceptable?: {batch.stress_summary['moderate_positive']}
- Parameter neighbor pass ratio: {batch.neighbor_pass_ratio:.2f}
- Monte Carlo median return: {monte_carlo['median_return']:.2f}
- Monte Carlo 1st percentile return: {monte_carlo['p01_return']:.2f}
- Monte Carlo 5th percentile return: {monte_carlo['p05_return']:.2f}
- Monte Carlo 95th percentile return: {monte_carlo['p95_return']:.2f}
### Stress scenario matrix
| Scenario | Return | Profit factor | Return / Max DD | Trades | Pass |
|---|---:|---:|---:|---:|---|
{"".join(f"| {row.scenario} | {row.total_return:.2f} | {row.profit_factor:.2f} | {row.return_to_max_drawdown:.2f} | {row.total_trades} | {row.passed} |{chr(10)}" for row in batch.stress_results.itertuples())}

## 14. Distribution of results
### By symbol
| Symbol | Return | Profit factor | Trades | Comment |
|---|---:|---:|---:|---|
{symbol_lines}

### By year
| Year | Return | Profit factor | Max DD | Trades |
|---|---:|---:|---:|---:|
{year_lines}

## 15. Acceptance criteria check
| Criterion | Pass / Fail | Comment |
|---|---|---|
{acceptance_lines}

## 16. Final verdict
- Final label: {batch.classification}
- Notes: {' '.join(batch.notes) if batch.notes else 'No extra notes.'}
"""

    def _render_smoke_test_report(
        self,
        *,
        strategy_name: str,
        run_mode: str,
        timeframe: str,
        symbols: list[str],
        start: str,
        end: str,
        parameters: dict[str, Any],
        artifacts: BacktestArtifacts,
        skipped_steps: list[str],
    ) -> str:
        metrics = artifacts.metrics
        average_position_size = float(artifacts.trades["position_size"].mean()) if not artifacts.trades.empty else 0.0
        average_risk_amount = float(artifacts.trades["risk_amount_usd"].mean()) if not artifacts.trades.empty else 0.0
        average_total_cost = (
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
        quality_lines = []
        for symbol in symbols:
            summary = artifacts.data_quality[symbol]
            issues = " | ".join(issue["message"] for issue in summary["issues"]) if summary["issues"] else "None"
            quality_lines.append(
                f"- {symbol}: status={summary['status']}, fatal={summary['fatal_count']}, "
                f"warning={summary['warning_count']}, issues={issues}"
            )
        yearly_lines = (
            "\n".join(
                f"| {row.year} | {row.return_:.2f} | {row.profit_factor:.2f} | {row.trades} |"
                for row in artifacts.yearly_results.rename(columns={"return": "return_"}).itertuples()
            )
            if not artifacts.yearly_results.empty
            else "| n/a | 0.00 | 0.00 | 0 |"
        )
        skipped_lines = "\n".join(f"- {step}" for step in skipped_steps)

        return f"""# Lightweight Smoke Test Report — {strategy_name}

## 1. Scope
- Run mode: {run_mode}
- Symbols: {', '.join(symbols)}
- Timeframe: {timeframe}
- Backtest window: {start} to {end}
- Parameters: {parameters}

## 2. Data audit
{chr(10).join(quality_lines)}

## 3. Backtest result
- Total return: {metrics.total_return:.2f}
- Profit factor: {metrics.profit_factor:.2f}
- Max drawdown: {metrics.max_drawdown:.2f}
- Return / Max DD: {metrics.return_to_max_drawdown:.2f}
- Win rate: {metrics.win_rate:.2%}
- Expectancy per trade: {metrics.expectancy_per_trade:.2f}
- Expectancy in R: {metrics.expectancy_r:.4f}
- Total trades: {metrics.total_trades}
- Max consecutive losses: {metrics.consecutive_losses_max}

## 4. Trade sanity checks
- Average position size: {average_position_size:.4f}
- Average intended risk amount (USD): {average_risk_amount:.2f}
- Average total explicit cost per trade (USD): {average_total_cost:.2f}
- Data sources: {artifacts.data_sources}

## 5. Yearly summary
| Year | Return | Profit factor | Trades |
|---|---:|---:|---:|
{yearly_lines}

## 6. Intentionally skipped for smoke mode
{skipped_lines}
"""

    def _render_bounded_research_report(
        self,
        *,
        symbol: str,
        timeframe: str,
        run_mode: str,
        start: str,
        end: str,
        runs: pd.DataFrame,
        best: pd.DataFrame,
    ) -> str:
        best_lines = "\n".join(
            f"- {row.strategy_name}: best parameter_index={row.parameter_index}, trades={row.trade_count}, "
            f"return={row.total_return:.2f}, pf={row.profit_factor:.2f}, max_dd={row.max_drawdown:.2f}, "
            f"return/max_dd={row.return_to_max_drawdown:.2f}, avg_cost={row.avg_explicit_cost_per_trade:.2f}"
            for row in best.itertuples()
        )
        run_lines = "\n".join(
            f"| {row.strategy_name} | {row.parameter_index} | {row.trade_count} | {row.total_return:.2f} | "
            f"{row.profit_factor:.2f} | {row.max_drawdown:.2f} | {row.return_to_max_drawdown:.2f} | "
            f"{row.avg_explicit_cost_per_trade:.2f} | {row.data_quality_status} |"
            for row in runs.itertuples()
        )
        consistency_lines = []
        for strategy_name, chunk in runs.groupby("strategy_name"):
            positive_runs = int((chunk["total_return"] > 0).sum())
            pf_above_one = int((chunk["profit_factor"] > 1.0).sum())
            consistency_lines.append(
                f"- {strategy_name}: {len(chunk)} bounded runs, positive runs={positive_runs}, pf>1 runs={pf_above_one}"
            )

        return f"""# Bounded Strategy Comparison Report

## 1. Scope
- Symbol: {symbol}
- Timeframe: {timeframe}
- Run mode: {run_mode}
- Backtest window: {start} to {end}
- Research shape: small bounded parameter subset only; no full pipeline

## 2. Best run per strategy
{best_lines}

## 3. All bounded runs
| Strategy | Param idx | Trades | Total return | Profit factor | Max DD | Return / Max DD | Avg explicit cost/trade | Data quality |
|---|---:|---:|---:|---:|---:|---:|---:|---|
{run_lines}

## 4. Small-subset consistency
{chr(10).join(consistency_lines)}

## 5. Intentionally skipped
- Broad parameter sweep
- Neighbor sensitivity grid
- Full walk-forward validation
- Full stress-test matrix
- Full train / validation / holdout research batch
"""
