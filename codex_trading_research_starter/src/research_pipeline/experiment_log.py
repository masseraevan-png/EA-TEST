from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd

from .evaluation import StrategyBatchResult


class ExperimentLogger:
    def __init__(self, repo_root: Path) -> None:
        self.path = repo_root / "EXPERIMENT_LOG.csv"

    def append(self, batch: StrategyBatchResult, timeframe: str, symbols: list[str]) -> None:
        log = pd.read_csv(self.path)
        if "run_mode" not in log.columns:
            log["run_mode"] = ""
        if "data_quality_status" not in log.columns:
            log["data_quality_status"] = ""
        if "data_quality_warnings" not in log.columns:
            log["data_quality_warnings"] = False
        if "data_quality_warning_count" not in log.columns:
            log["data_quality_warning_count"] = 0
        data_quality_summaries = [
            batch.train.data_quality[symbol]
            for symbol in symbols
            if symbol in batch.train.data_quality
        ]
        row = {
            "experiment_id": uuid4().hex[:12],
            "date_utc": pd.Timestamp.utcnow().isoformat(),
            "research_phase": "phase_1_simple_interpretable_strategies",
            "run_mode": batch.run_mode,
            "strategy_name": batch.strategy_name,
            "hypothesis_family": batch.strategy_name,
            "symbols": "|".join(symbols),
            "timeframe": timeframe,
            "train_period": "2018-01-01:2022-12-31",
            "validation_period": "2023-01-01:2023-12-31",
            "test_period": "2024-01-01:2024-12-31",
            "holdout_period": "2025-01-01:2025-12-31",
            "holdout_used_for_selection": False,
            "parameter_set_id": uuid4().hex[:8],
            "parameter_summary": str(batch.selected_parameters),
            "cost_model": "symbol_specific_explicit_units",
            "is_total_trades": batch.train.metrics.total_trades,
            "validation_trades": batch.validation.metrics.total_trades,
            "test_trades": batch.test.metrics.total_trades,
            "holdout_trades": batch.holdout.metrics.total_trades,
            "oos_trades": batch.combined_oos.metrics.total_trades,
            "is_net_pnl": batch.train.metrics.total_return,
            "validation_net_pnl": batch.validation.metrics.total_return,
            "test_net_pnl": batch.test.metrics.total_return,
            "holdout_net_pnl": batch.holdout.metrics.total_return,
            "is_profit_factor": batch.train.metrics.profit_factor,
            "validation_profit_factor": batch.validation.metrics.profit_factor,
            "test_profit_factor": batch.test.metrics.profit_factor,
            "holdout_profit_factor": batch.holdout.metrics.profit_factor,
            "oos_profit_factor": batch.combined_oos.metrics.profit_factor,
            "oos_return_to_max_dd": batch.combined_oos.metrics.return_to_max_drawdown,
            "holdout_return_to_max_dd": batch.holdout.metrics.return_to_max_drawdown,
            "neighbor_pass_ratio": batch.neighbor_pass_ratio,
            "walk_forward_windows": batch.walkforward_summary["total_windows"],
            "walk_forward_passes": batch.walkforward_summary["passed_windows"],
            "cost_stress_result": "captured_in_report",
            "monte_carlo_result": "captured_in_report",
            "final_label": batch.classification,
            "notes": " | ".join(batch.notes) if batch.notes else "",
            "data_quality_status": "|".join(
                f"{symbol}:{batch.train.data_quality[symbol]['status']}"
                for symbol in symbols
                if symbol in batch.train.data_quality
            ),
            "data_quality_warnings": any(summary["warning_count"] > 0 for summary in data_quality_summaries),
            "data_quality_warning_count": sum(summary["warning_count"] for summary in data_quality_summaries),
        }
        updated = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
        updated.to_csv(self.path, index=False)
