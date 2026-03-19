from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd
from dateutil.relativedelta import relativedelta

from .backtest import BacktestRunner
from .config import ResearchConfig
from .interfaces import BaseStrategy


@dataclass
class WalkForwardWindow:
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    selected_parameters: dict[str, Any]
    train_return: float
    train_profit_factor: float
    train_trades: int
    validation_return: float
    validation_profit_factor: float
    validation_trades: int
    test_return: float
    test_profit_factor: float
    test_trades: int
    passed: bool


@dataclass
class WalkForwardSummary:
    total_windows: int
    passed_windows: int
    pass_ratio: float
    average_test_return: float
    average_test_profit_factor: float
    best_window_return: float
    worst_window_return: float
    test_return_std: float
    test_profit_factor_std: float


class WalkForwardRunner:
    def __init__(self, runner: BacktestRunner, config: ResearchConfig) -> None:
        self.runner = runner
        self.config = config

    def run(self, strategy: BaseStrategy, symbols: list[str], timeframe: str) -> tuple[list[WalkForwardWindow], WalkForwardSummary]:
        split = self.config.split
        current = pd.Timestamp(split["train_start"])
        final_end = pd.Timestamp(split["test_end"])
        train_months = int(self.config.raw["walk_forward"]["train_months"])
        validation_months = int(self.config.raw["walk_forward"]["validation_months"])
        test_months = int(self.config.raw["walk_forward"]["test_months"])
        step_months = int(self.config.raw["walk_forward"]["step_months"])
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
            selected_parameters, train_result, validation_result = self._select_parameters_for_window(
                strategy=strategy,
                symbols=symbols,
                timeframe=timeframe,
                train_start=str(train_start.date()),
                train_end=str(train_end.date()),
                validation_start=str(validation_start.date()),
                validation_end=str(validation_end.date()),
            )
            test_result = self.runner.run(
                strategy,
                selected_parameters,
                symbols,
                timeframe,
                str(test_start.date()),
                str(test_end.date()),
            )
            passed = (
                test_result.metrics.profit_factor >= self.config.raw["filters"]["min_oos_profit_factor"]
                and test_result.metrics.total_return > 0
            )
            windows.append(
                WalkForwardWindow(
                    train_start=str(train_start.date()),
                    train_end=str(train_end.date()),
                    validation_start=str(validation_start.date()),
                    validation_end=str(validation_end.date()),
                    test_start=str(test_start.date()),
                    test_end=str(test_end.date()),
                    selected_parameters=selected_parameters,
                    train_return=train_result.metrics.total_return,
                    train_profit_factor=train_result.metrics.profit_factor,
                    train_trades=train_result.metrics.total_trades,
                    validation_return=validation_result.metrics.total_return,
                    validation_profit_factor=validation_result.metrics.profit_factor,
                    validation_trades=validation_result.metrics.total_trades,
                    test_return=test_result.metrics.total_return,
                    test_profit_factor=test_result.metrics.profit_factor,
                    test_trades=test_result.metrics.total_trades,
                    passed=passed,
                )
            )
            current = current + relativedelta(months=step_months)
        return windows, self._summarize(windows)

    def _select_parameters_for_window(
        self,
        strategy: BaseStrategy,
        symbols: list[str],
        timeframe: str,
        train_start: str,
        train_end: str,
        validation_start: str,
        validation_end: str,
    ) -> tuple[dict[str, Any], Any, Any]:
        ranked: list[tuple[float, dict[str, Any], Any, Any]] = []
        for params in strategy.parameter_grid():
            train = self.runner.run(strategy, params, symbols, timeframe, train_start, train_end)
            validation = self.runner.run(
                strategy, params, symbols, timeframe, validation_start, validation_end
            )
            score = (
                validation.metrics.return_to_max_drawdown
                + validation.metrics.expectancy_r
                + min(validation.metrics.total_trades / 100.0, 3.0)
            )
            ranked.append((score, params, train, validation))
        ranked.sort(key=lambda item: (item[0], item[3].metrics.profit_factor), reverse=True)
        _, params, train_result, validation_result = ranked[0]
        return params, train_result, validation_result

    @staticmethod
    def _summarize(windows: list[WalkForwardWindow]) -> WalkForwardSummary:
        if not windows:
            return WalkForwardSummary(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        test_returns = pd.Series([window.test_return for window in windows], dtype=float)
        test_pf = pd.Series([window.test_profit_factor for window in windows], dtype=float)
        passed_windows = sum(1 for window in windows if window.passed)
        return WalkForwardSummary(
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
