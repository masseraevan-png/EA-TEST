from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .backtest import BacktestArtifacts, BacktestRunner
from .config import ResearchConfig
from .interfaces import BaseStrategy


@dataclass
class StrategyBatchResult:
    strategy_name: str
    run_mode: str
    selected_parameters: dict[str, Any]
    train: BacktestArtifacts
    validation: BacktestArtifacts
    test: BacktestArtifacts
    holdout: BacktestArtifacts
    combined_oos: BacktestArtifacts
    by_symbol_oos: pd.DataFrame
    neighborhood: pd.DataFrame
    neighbor_pass_ratio: float
    classification: str
    acceptance_rows: list[dict[str, str]]
    notes: list[str]
    walkforward_summary: dict[str, Any]
    stress_results: pd.DataFrame
    stress_summary: dict[str, Any]


class ParameterSweep:
    def __init__(self, runner: BacktestRunner, config: ResearchConfig) -> None:
        self.runner = runner
        self.config = config

    def select_parameters(
        self,
        strategy: BaseStrategy,
        symbols: list[str],
        timeframe: str,
    ) -> tuple[dict[str, Any], pd.DataFrame]:
        rows: list[dict[str, Any]] = []
        split = self.config.split
        for params in strategy.parameter_grid():
            train = self.runner.run(strategy, params, symbols, timeframe, split["train_start"], split["train_end"])
            validation = self.runner.run(strategy, params, symbols, timeframe, split["validation_start"], split["validation_end"])
            score = validation.metrics.return_to_max_drawdown + validation.metrics.expectancy_r + min(validation.metrics.total_trades / 100.0, 3.0)
            rows.append(
                {
                    "parameters": params,
                    "train_trades": train.metrics.total_trades,
                    "validation_trades": validation.metrics.total_trades,
                    "validation_pf": validation.metrics.profit_factor,
                    "validation_r_to_dd": validation.metrics.return_to_max_drawdown,
                    "validation_expectancy_r": validation.metrics.expectancy_r,
                    "score": score,
                }
            )
        summary = pd.DataFrame(rows).sort_values(["score", "validation_pf"], ascending=False).reset_index(drop=True)
        return dict(summary.iloc[0]["parameters"]), summary


class StressTester:
    def __init__(self, runner: BacktestRunner, config: ResearchConfig) -> None:
        self.runner = runner
        self.config = config

    def run(
        self,
        strategy: BaseStrategy,
        parameters: dict[str, Any],
        symbols: list[str],
        timeframe: str,
        start: str,
        end: str,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        from .backtest import ExecutionOverrides

        scenarios = [
            ("base", (1.0, 1.0, 1.0), ExecutionOverrides()),
            ("moderate_cost", (1.25, 1.25, 1.0), ExecutionOverrides()),
            ("higher_cost", (1.5, 1.5, 1.25), ExecutionOverrides()),
            ("spread_shock", (2.0, 1.0, 1.0), ExecutionOverrides()),
            ("slippage_shock", (1.0, 2.0, 1.0), ExecutionOverrides()),
            ("commission_shock", (1.0, 1.0, 1.25), ExecutionOverrides()),
            ("delayed_entry", (1.25, 1.25, 1.0), ExecutionOverrides(entry_delay_bars=1)),
            ("skip_5pct", (1.25, 1.25, 1.0), ExecutionOverrides(trade_skip_rate=0.05)),
            ("skip_10pct", (1.5, 1.5, 1.25), ExecutionOverrides(trade_skip_rate=0.10)),
            (
                "harsh_execution",
                (1.5, 2.0, 1.25),
                ExecutionOverrides(entry_delay_bars=1, trade_skip_rate=0.10, adverse_exit_slippage_multiplier=1.0),
            ),
        ]
        rows: list[dict[str, Any]] = []
        for name, cost_multipliers, overrides in scenarios:
            result = self.runner.run(
                strategy,
                parameters,
                symbols,
                timeframe,
                start,
                end,
                cost_multipliers=cost_multipliers,
                execution_overrides=overrides,
            )
            passed = (
                result.metrics.total_return > 0
                and result.metrics.profit_factor >= self.config.raw["filters"]["min_oos_profit_factor"]
            )
            rows.append(
                {
                    "scenario": name,
                    "spread_multiplier": cost_multipliers[0],
                    "slippage_multiplier": cost_multipliers[1],
                    "commission_multiplier": cost_multipliers[2],
                    "entry_delay_bars": overrides.entry_delay_bars,
                    "trade_skip_rate": overrides.trade_skip_rate,
                    "adverse_exit_slippage_multiplier": overrides.adverse_exit_slippage_multiplier,
                    "total_return": result.metrics.total_return,
                    "profit_factor": result.metrics.profit_factor,
                    "return_to_max_drawdown": result.metrics.return_to_max_drawdown,
                    "total_trades": result.metrics.total_trades,
                    "passed": passed,
                }
            )
        table = pd.DataFrame(rows)
        if table.empty:
            return table, {"pass_rate": 0.0, "average_return": 0.0, "worst_return": 0.0, "worst_profit_factor": 0.0, "moderate_positive": False}
        moderate_row = table.loc[table["scenario"] == "moderate_cost"].iloc[0]
        summary = {
            "pass_rate": float(table["passed"].mean()),
            "average_return": float(table["total_return"].mean()),
            "worst_return": float(table["total_return"].min()),
            "worst_profit_factor": float(table["profit_factor"].min()),
            "moderate_positive": bool(moderate_row["total_return"] > 0 and moderate_row["profit_factor"] >= self.config.raw["filters"]["min_oos_profit_factor"]),
        }
        return table, summary


class AcceptanceEvaluator:
    def __init__(self, config: ResearchConfig) -> None:
        self.config = config
        self.filters = config.raw["filters"]

    def classify(
        self,
        total_trades: int,
        train_trades: int,
        validation_trades: int,
        test_trades: int,
        oos_trades: int,
        oos_pf: float,
        oos_expectancy_r: float,
        oos_return_to_dd: float,
        positive_symbols: int,
        max_symbol_share: float,
        cost_stress_positive: bool,
        neighbor_pass_ratio: float,
        wf_windows: int,
        wf_passes: int,
        wf_pass_ratio: float,
        wf_average_pf: float,
        stress_pass_rate: float,
        stress_average_return: float,
        stress_worst_return: float,
        stress_worst_pf: float,
        stress_moderate_positive: bool,
        holdout_trades: int,
        holdout_pf: float,
        holdout_return_to_dd: float,
        holdout_return: float,
    ) -> tuple[str, list[dict[str, str]], list[str]]:
        rows: list[dict[str, str]] = []
        notes: list[str] = []

        def add(name: str, passed: bool, comment: str) -> None:
            rows.append({"criterion": name, "status": "Pass" if passed else "Fail", "comment": comment})

        add("Min total trades", total_trades >= self.filters["min_total_trades"], f"Observed {total_trades}")
        add("Min OOS trades", oos_trades >= self.filters["min_oos_trades"], f"Observed {oos_trades}")
        add("OOS profit factor", oos_pf >= self.filters["min_oos_profit_factor"], f"Observed {oos_pf:.2f}")
        add("OOS expectancy in R", oos_expectancy_r > self.filters["min_oos_expectancy_r"], f"Observed {oos_expectancy_r:.3f}")
        add("OOS return / max DD", oos_return_to_dd >= self.filters["min_oos_return_to_max_dd"], f"Observed {oos_return_to_dd:.2f}")
        add("Cross-symbol distribution", positive_symbols >= self.filters["min_symbols_with_positive_oos"] and max_symbol_share <= self.filters["max_single_symbol_profit_share"], f"Positive symbols {positive_symbols}, max share {max_symbol_share:.2f}")
        add(
            "Cost robustness",
            cost_stress_positive and stress_moderate_positive and stress_pass_rate >= 0.50 and stress_average_return > 0,
            f"pass_rate={stress_pass_rate:.2f}, avg_return={stress_average_return:.2f}, worst_return={stress_worst_return:.2f}, worst_pf={stress_worst_pf:.2f}",
        )
        add("Parameter stability", neighbor_pass_ratio >= self.config.raw["stress_tests"]["parameter_neighborhood"]["min_neighbor_pass_ratio"], f"Observed {neighbor_pass_ratio:.2f}")
        add(
            "Walk-forward consistency",
            wf_windows >= self.config.raw["walk_forward"]["min_windows"] and wf_pass_ratio >= 0.50,
            f"Windows={wf_windows}, passes={wf_passes}, pass_ratio={wf_pass_ratio:.2f}, avg_pf={wf_average_pf:.2f}",
        )
        holdout_ok = holdout_trades < 20 or (holdout_pf >= 0.95 and holdout_return_to_dd >= 0.50 and holdout_return >= 0)
        add("Holdout sanity", holdout_ok, f"Trades={holdout_trades}, PF={holdout_pf:.2f}, Return/DD={holdout_return_to_dd:.2f}")
        add("Simplicity / interpretability", True, "Phase 1 strategies remain simple and explainable")

        hard_fail = any(row["status"] == "Fail" for row in rows[:9]) or not holdout_ok
        survivor = all(row["status"] == "Pass" for row in rows)
        if survivor:
            label = "Survivor candidate"
        elif hard_fail:
            label = "Rejected"
        else:
            label = "Needs more validation"
        if label != "Survivor candidate":
            notes.append("The framework remains conservative and does not claim the strategy is proven.")
        return label, rows, notes


def combine_artifacts(chunks: list[BacktestArtifacts]) -> BacktestArtifacts:
    trades = pd.concat([chunk.trades for chunk in chunks], ignore_index=True) if chunks else pd.DataFrame()
    equity = pd.concat([chunk.equity_curve for chunk in chunks], ignore_index=True) if chunks else pd.DataFrame()
    from .metrics import compute_metrics, monthly_returns, by_year

    metrics = compute_metrics(trades, equity) if not trades.empty else compute_metrics(pd.DataFrame(columns=["pnl", "r_multiple"]), pd.DataFrame(columns=["timestamp", "drawdown"]))
    return BacktestArtifacts(
        trades=trades,
        equity_curve=equity,
        metrics=metrics,
        monthly_returns=monthly_returns(trades),
        yearly_results=by_year(trades),
        data_sources={
            symbol: source
            for chunk in chunks
            for symbol, source in chunk.data_sources.items()
        },
        data_quality={
            symbol: summary
            for chunk in chunks
            for symbol, summary in chunk.data_quality.items()
        },
    )


def build_neighbor_grid(parameters: dict[str, Any]) -> list[dict[str, Any]]:
    numeric_keys = [key for key, value in parameters.items() if isinstance(value, (int, float)) and not isinstance(value, bool)]
    neighbors: list[dict[str, Any]] = []
    for key in numeric_keys:
        value = parameters[key]
        step = 1 if isinstance(value, int) else 0.2
        for delta in (-step, step):
            candidate = value + delta
            if candidate <= 0:
                continue
            neighbor = dict(parameters)
            neighbor[key] = candidate
            neighbors.append(neighbor)
    return neighbors


def monte_carlo_summary(trades: pd.DataFrame, iterations: int, seed: int = 7) -> dict[str, float]:
    if trades.empty:
        return {"median_return": 0.0, "p05_return": 0.0, "p95_return": 0.0}
    rng = np.random.default_rng(seed)
    pnls = trades["pnl"].to_numpy()
    totals = []
    for _ in range(iterations):
        shuffled = rng.permutation(pnls)
        totals.append(float(shuffled.sum()))
        boot = rng.choice(pnls, size=len(pnls), replace=True)
        totals.append(float(boot.sum()))
        if len(pnls) >= 5:
            block_size = min(5, len(pnls))
            blocks = []
            while len(blocks) < len(pnls):
                start = int(rng.integers(0, len(pnls) - block_size + 1))
                blocks.extend(pnls[start : start + block_size])
            totals.append(float(np.array(blocks[: len(pnls)]).sum()))
    return {
        "median_return": float(np.median(totals)),
        "p01_return": float(np.quantile(totals, 0.01)),
        "p05_return": float(np.quantile(totals, 0.05)),
        "p95_return": float(np.quantile(totals, 0.95)),
    }
