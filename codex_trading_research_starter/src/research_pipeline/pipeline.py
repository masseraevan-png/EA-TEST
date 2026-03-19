from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import BacktestRunner
from .config import ResearchConfig, load_config
from .evaluation import AcceptanceEvaluator, ParameterSweep, StrategyBatchResult, StressTester, build_neighbor_grid, combine_artifacts
from .experiment_log import ExperimentLogger
from .reporting import ReportWriter
from .strategies.mean_reversion import MeanReversionAfterExpansionStrategy
from .strategies.price_action import LiquiditySweepReversalStrategy, OpeningDrivePullbackStrategy
from .strategies.session_breakout import SessionBreakoutStrategy
from .walkforward import WalkForwardRunner


STRATEGY_REGISTRY = {
    "session_breakout": SessionBreakoutStrategy,
    "mean_reversion_after_expansion": MeanReversionAfterExpansionStrategy,
    "liquidity_sweep_reversal": LiquiditySweepReversalStrategy,
    "opening_drive_pullback": OpeningDrivePullbackStrategy,
}


class ResearchPipeline:
    def __init__(self, repo_root: Path, config_path: Path, run_mode: str | None = None) -> None:
        self.repo_root = repo_root
        self.config = load_config(config_path)
        self.run_mode = self.config.resolve_run_mode(run_mode)
        self.runner = BacktestRunner(repo_root=repo_root, config=self.config, run_mode=self.run_mode)
        self.sweeper = ParameterSweep(self.runner, self.config)
        self.stress_tester = StressTester(self.runner, self.config)
        self.evaluator = AcceptanceEvaluator(self.config)
        self.walkforward = WalkForwardRunner(self.runner, self.config)
        self.reporter = ReportWriter(repo_root)
        self.logger = ExperimentLogger(repo_root)

    def available_strategies(self) -> list[str]:
        return sorted(STRATEGY_REGISTRY)

    def run_batch(self, strategy_name: str, timeframe: str | None = None, symbols: list[str] | None = None) -> dict[str, Any]:
        timeframe = timeframe or self.config.default_timeframe
        symbols = symbols or self.config.symbols
        strategy = STRATEGY_REGISTRY[strategy_name]()
        selected_parameters, sweep_summary = self.sweeper.select_parameters(strategy, symbols, timeframe)
        split = self.config.split
        train = self.runner.run(strategy, selected_parameters, symbols, timeframe, split["train_start"], split["train_end"])
        validation = self.runner.run(strategy, selected_parameters, symbols, timeframe, split["validation_start"], split["validation_end"])
        test = self.runner.run(strategy, selected_parameters, symbols, timeframe, split["test_start"], split["test_end"])
        holdout = self.runner.run(strategy, selected_parameters, symbols, timeframe, split["holdout_start"], split["holdout_end"])
        combined_oos = combine_artifacts([validation, test])
        by_symbol_rows = []
        for symbol in symbols:
            symbol_trades = combined_oos.trades.loc[combined_oos.trades["symbol"] == symbol]
            wins = symbol_trades.loc[symbol_trades["pnl"] > 0, "pnl"].sum()
            losses = abs(symbol_trades.loc[symbol_trades["pnl"] < 0, "pnl"].sum())
            pf = wins / losses if losses else float("inf") if wins > 0 else 0.0
            by_symbol_rows.append({"symbol": symbol, "total_return": float(symbol_trades["pnl"].sum()), "profit_factor": float(pf), "total_trades": int(len(symbol_trades))})
        by_symbol = pd.DataFrame(by_symbol_rows)
        profit_share = 0.0
        positive_symbols = int((by_symbol["total_return"] > 0).sum()) if not by_symbol.empty else 0
        if combined_oos.metrics.total_return > 0 and not by_symbol.empty:
            profit_share = float(by_symbol["total_return"].max() / combined_oos.metrics.total_return)
        moderate = self.runner.run(strategy, selected_parameters, symbols, timeframe, split["validation_start"], split["test_end"], cost_multipliers=(1.25, 1.25, 1.0))
        cost_stress_positive = moderate.metrics.total_return >= 0
        stress_results, stress_summary = self.stress_tester.run(
            strategy,
            selected_parameters,
            symbols,
            timeframe,
            split["validation_start"],
            split["test_end"],
        )
        neighbors = []
        for neighbor in build_neighbor_grid(selected_parameters):
            result = self.runner.run(strategy, neighbor, symbols, timeframe, split["validation_start"], split["test_end"])
            neighbors.append({
                "parameters": neighbor,
                "total_return": result.metrics.total_return,
                "profit_factor": result.metrics.profit_factor,
                "pass": result.metrics.total_return >= 0 and result.metrics.profit_factor >= self.config.raw["filters"]["min_oos_profit_factor"],
            })
        neighborhood = pd.DataFrame(neighbors)
        neighbor_pass_ratio = float(neighborhood["pass"].mean()) if not neighborhood.empty else 0.0
        wf_windows, wf_summary = self.walkforward.run(strategy, symbols, timeframe)
        wf_passes = wf_summary.passed_windows
        classification, acceptance_rows, notes = self.evaluator.classify(
            total_trades=train.metrics.total_trades + validation.metrics.total_trades + test.metrics.total_trades,
            train_trades=train.metrics.total_trades,
            validation_trades=validation.metrics.total_trades,
            test_trades=test.metrics.total_trades,
            oos_trades=combined_oos.metrics.total_trades,
            oos_pf=combined_oos.metrics.profit_factor,
            oos_expectancy_r=combined_oos.metrics.expectancy_r,
            oos_return_to_dd=combined_oos.metrics.return_to_max_drawdown,
            positive_symbols=positive_symbols,
            max_symbol_share=profit_share,
            cost_stress_positive=cost_stress_positive,
            neighbor_pass_ratio=neighbor_pass_ratio,
            wf_windows=wf_summary.total_windows,
            wf_passes=wf_passes,
            wf_pass_ratio=wf_summary.pass_ratio,
            wf_average_pf=wf_summary.average_test_profit_factor,
            stress_pass_rate=stress_summary["pass_rate"],
            stress_average_return=stress_summary["average_return"],
            stress_worst_return=stress_summary["worst_return"],
            stress_worst_pf=stress_summary["worst_profit_factor"],
            stress_moderate_positive=stress_summary["moderate_positive"],
            holdout_trades=holdout.metrics.total_trades,
            holdout_pf=holdout.metrics.profit_factor,
            holdout_return_to_dd=holdout.metrics.return_to_max_drawdown,
            holdout_return=holdout.metrics.total_return,
        )
        batch = StrategyBatchResult(
            strategy_name=strategy_name,
            run_mode=self.run_mode,
            selected_parameters=selected_parameters,
            train=train,
            validation=validation,
            test=test,
            holdout=holdout,
            combined_oos=combined_oos,
            by_symbol_oos=by_symbol,
            neighborhood=neighborhood,
            neighbor_pass_ratio=neighbor_pass_ratio,
            classification=classification,
            acceptance_rows=acceptance_rows,
            notes=notes,
            walkforward_summary=asdict(wf_summary),
            stress_results=stress_results,
            stress_summary=stress_summary,
        )
        paths = self.reporter.write_batch_outputs(
            batch,
            walkforward_rows=[asdict(row) for row in wf_windows],
            strategy_hypothesis=strategy.spec.hypothesis,
            strategy_description=strategy.spec.long_description,
            timeframe=timeframe,
            symbols=symbols,
            symbol_unit_notes=[
                f"{symbol}: {self.config.mechanics_for_symbol(symbol).describe()}"
                for symbol in symbols
            ],
            data_source_notes=[
                f"{symbol}: {combined_oos.data_sources.get(symbol) or train.data_sources.get(symbol) or 'unknown'}"
                for symbol in symbols
            ],
            data_quality_notes=[
                f"{symbol}: status={train.data_quality[symbol]['status']}, "
                f"fatal={train.data_quality[symbol]['fatal_count']}, "
                f"warning={train.data_quality[symbol]['warning_count']}"
                + (
                    f", issues={' | '.join(issue['message'] for issue in train.data_quality[symbol]['issues'])}"
                    if train.data_quality[symbol]["issues"]
                    else ""
                )
                for symbol in symbols
                if symbol in train.data_quality
            ],
            data_quality_warning_details=[
                f"{symbol}: {issue['message']}"
                for symbol in symbols
                if symbol in train.data_quality
                for issue in train.data_quality[symbol]["issues"]
                if issue["severity"] == "warning" and "same-day intraday gap" in issue["message"]
            ],
        )
        self.logger.append(batch, timeframe, symbols)
        return {
            "batch": batch,
            "paths": {key: str(path) for key, path in paths.items()},
            "sweep_summary": sweep_summary,
            "walkforward_rows": [asdict(row) for row in wf_windows],
        }
