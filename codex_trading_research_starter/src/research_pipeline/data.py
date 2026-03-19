from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import ResearchConfig


@dataclass(frozen=True)
class DatasetBundle:
    bars: pd.DataFrame
    source: str
    quality_summary: dict[str, Any]


class MarketDataLoader:
    """Loads CSV data when available; otherwise creates deterministic synthetic bars for framework demos."""

    def __init__(self, repo_root: Path, config: ResearchConfig, run_mode: str) -> None:
        self.repo_root = repo_root
        self.config = config
        self.run_mode = run_mode
        self.data_dir = repo_root / "data"
        self._cache: dict[tuple[str, str], DatasetBundle] = {}

    def load_symbol(self, symbol: str, timeframe: str) -> DatasetBundle:
        cache_key = (symbol, timeframe)
        if cache_key in self._cache:
            return self._cache[cache_key]
        csv_path = self.data_dir / f"{symbol}_{timeframe}.csv"
        if csv_path.exists():
            bars = pd.read_csv(csv_path)
            source = str(csv_path.relative_to(self.repo_root))
        elif self.run_mode == "demo_mode":
            bars = self._generate_synthetic_bars(symbol=symbol, timeframe=timeframe)
            source = f"synthetic::{symbol}_{timeframe}"
        else:
            raise FileNotFoundError(
                f"Real research mode requires CSV data for {symbol} {timeframe}. "
                f"Expected file: {csv_path}. Synthetic fallback is disabled in real_research_mode."
            )
        quality_summary, cleaned_bars = self._audit_bars(symbol, timeframe, bars, source)
        if self.run_mode == "real_research_mode" and quality_summary["fatal_count"] > 0:
            raise ValueError(
                f"Data-quality audit failed for {symbol} {timeframe}: "
                f"{'; '.join(issue['message'] for issue in quality_summary['issues'] if issue['severity'] == 'fatal')}"
            )
        bundle = DatasetBundle(bars=cleaned_bars, source=source, quality_summary=quality_summary)
        self._cache[cache_key] = bundle
        return bundle

    def _validate_bars(self, symbol: str, bars: pd.DataFrame) -> None:
        required = self.config.raw["data"]["require_ohlcv_columns"]
        missing = [column for column in required if column not in bars.columns]
        if missing:
            raise ValueError(f"{symbol} data missing required columns: {missing}")
        if len(bars) < int(self.config.raw["data"]["min_history_bars_per_symbol"]):
            raise ValueError(f"{symbol} has insufficient history: {len(bars)} bars")

    def _audit_bars(
        self,
        symbol: str,
        timeframe: str,
        bars: pd.DataFrame,
        source: str,
    ) -> tuple[dict[str, Any], pd.DataFrame]:
        issues: list[dict[str, str]] = []
        frame = bars.copy()
        self._validate_bars(symbol, frame)
        try:
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
        except Exception as exc:
            issues.append({"severity": "fatal", "message": f"Unparseable timestamps: {exc}"})
            return self._build_quality_summary(symbol, timeframe, source, issues, frame), frame

        if not frame["timestamp"].is_monotonic_increasing:
            issues.append({"severity": "fatal", "message": "Timestamps are not strictly ordered ascending."})
        if frame["timestamp"].duplicated().any():
            issues.append({"severity": "fatal", "message": "Duplicate timestamps detected."})

        impossible_mask = (
            (frame["high"] < frame["low"])
            | (frame["open"] > frame["high"])
            | (frame["open"] < frame["low"])
            | (frame["close"] > frame["high"])
            | (frame["close"] < frame["low"])
            | (frame[["open", "high", "low", "close"]] <= 0).any(axis=1)
        )
        if impossible_mask.any():
            issues.append({"severity": "fatal", "message": f"Impossible OHLC values found in {int(impossible_mask.sum())} rows."})

        expected_delta = pd.Timedelta(minutes=5 if timeframe == "M5" else 15)
        diffs = frame["timestamp"].diff()
        large_intraday_gap_rows = self._collect_same_day_gaps(frame, diffs, expected_delta)
        issues.extend(self._classify_same_day_intraday_gaps(large_intraday_gap_rows, expected_delta))
        nonzero_diffs = diffs.dropna()
        irregular_gaps = nonzero_diffs[(nonzero_diffs > expected_delta) & (nonzero_diffs <= expected_delta * 3)]
        if not irregular_gaps.empty:
            issues.append({"severity": "warning", "message": f"Detected {len(irregular_gaps)} smaller missing-bar gaps."})

        median_delta = diffs.median() if not diffs.empty else expected_delta
        if median_delta != expected_delta:
            issues.append({"severity": "warning", "message": f"Median timestamp spacing {median_delta} does not match expected timeframe {expected_delta}."})

        weekend_rows = frame["timestamp"].dt.weekday >= 5
        if weekend_rows.any():
            issues.append({"severity": "warning", "message": f"Weekend bars detected: {int(weekend_rows.sum())} rows."})

        excluded_ranges = self.config.raw["sessions"].get("exclude_hours", [])
        excluded_hits = 0
        for excluded in excluded_ranges:
            start_text, end_text = excluded.split("-")
            start_hour = int(start_text.split(":")[0])
            end_hour = int(end_text.split(":")[0])
            excluded_hits += int(frame["timestamp"].dt.hour.between(start_hour, end_hour).sum())
        if excluded_hits:
            issues.append({"severity": "warning", "message": f"Bars found inside excluded-hours windows: {excluded_hits} rows."})

        split = self.config.split
        for split_name, start_key, end_key in [
            ("train", "train_start", "train_end"),
            ("validation", "validation_start", "validation_end"),
            ("test", "test_start", "test_end"),
            ("holdout", "holdout_start", "holdout_end"),
        ]:
            mask = (frame["timestamp"] >= pd.Timestamp(split[start_key])) & (frame["timestamp"] <= pd.Timestamp(split[end_key]))
            if not mask.any():
                issues.append({"severity": "fatal", "message": f"No bars found for required {split_name} period."})

        if not source.startswith("synthetic::"):
            expected_name = f"{symbol}_{timeframe}.csv"
            if Path(source).name != expected_name:
                issues.append({"severity": "warning", "message": f"CSV filename {Path(source).name} does not match expected {expected_name}."})

        return self._build_quality_summary(symbol, timeframe, source, issues, frame), frame

    @staticmethod
    def _collect_same_day_gaps(
        frame: pd.DataFrame,
        diffs: pd.Series,
        expected_delta: pd.Timedelta,
    ) -> list[dict[str, Any]]:
        same_day_mask = (
            diffs.gt(expected_delta * 3)
            & frame["timestamp"].shift(1).dt.date.eq(frame["timestamp"].dt.date)
        ).fillna(False)
        gap_rows: list[dict[str, Any]] = []
        for idx in frame.index[same_day_mask]:
            previous_timestamp = frame.at[idx - 1, "timestamp"]
            current_timestamp = frame.at[idx, "timestamp"]
            gap_rows.append(
                {
                    "previous_timestamp": previous_timestamp,
                    "timestamp": current_timestamp,
                    "gap": current_timestamp - previous_timestamp,
                    "missing_bars": int(((current_timestamp - previous_timestamp) / expected_delta) - 1),
                }
            )
        return gap_rows

    @staticmethod
    def _classify_same_day_intraday_gaps(
        gap_rows: list[dict[str, Any]],
        expected_delta: pd.Timedelta,
    ) -> list[dict[str, str]]:
        if not gap_rows:
            return []
        gap_dates = [row["timestamp"].date() for row in gap_rows]
        gaps_per_day = Counter(gap_dates)
        sorted_dates = sorted(set(gap_dates))
        min_days_apart = min(
            (current - previous).days
            for previous, current in zip(sorted_dates, sorted_dates[1:])
        ) if len(sorted_dates) > 1 else None

        warning_eligible = (
            len(gap_rows) <= 2
            and max(gaps_per_day.values()) == 1
            and all(row["gap"] <= expected_delta * 8 for row in gap_rows)
            and (min_days_apart is None or min_days_apart >= 20)
        )
        gap_details = "; ".join(
            f"{row['previous_timestamp']} -> {row['timestamp']} ({row['gap']}, missing {row['missing_bars']} bars)"
            for row in gap_rows
        )
        if warning_eligible:
            return [
                {
                    "severity": "warning",
                    "message": f"Detected {len(gap_rows)} isolated same-day intraday gap(s): {gap_details}",
                }
            ]
        return [
            {
                "severity": "fatal",
                "message": (
                    f"Detected {len(gap_rows)} repeated/clustered same-day intraday gap(s) beyond expected cadence: {gap_details}"
                ),
            }
        ]

    @staticmethod
    def _build_quality_summary(
        symbol: str,
        timeframe: str,
        source: str,
        issues: list[dict[str, str]],
        bars: pd.DataFrame,
    ) -> dict[str, Any]:
        fatal_count = sum(1 for issue in issues if issue["severity"] == "fatal")
        warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
        if source.startswith("synthetic::"):
            status = "demo_synthetic"
        elif fatal_count:
            status = "fatal"
        elif warning_count:
            status = "warning"
        else:
            status = "clean"
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": source,
            "status": status,
            "fatal_count": fatal_count,
            "warning_count": warning_count,
            "issues": issues,
            "bar_count": int(len(bars)),
            "start_timestamp": str(bars["timestamp"].min()) if "timestamp" in bars.columns else "",
            "end_timestamp": str(bars["timestamp"].max()) if "timestamp" in bars.columns else "",
        }

    def _generate_synthetic_bars(self, symbol: str, timeframe: str) -> pd.DataFrame:
        freq = "5min" if timeframe == "M5" else "15min"
        business_days = pd.date_range("2018-01-01", "2025-12-31", freq="B", tz="UTC")[::10]
        intraday_times = pd.date_range("07:00", "16:55" if timeframe == "M5" else "16:45", freq=freq).time
        timestamps = pd.DatetimeIndex([
            pd.Timestamp.combine(day.date(), intraday_time).tz_localize("UTC")
            for day in business_days
            for intraday_time in intraday_times
        ])
        n = len(timestamps)
        seed = abs(hash((symbol, timeframe))) % (2**32)
        rng = np.random.default_rng(seed)
        symbol_bias = {
            "EURUSD": 0.00001,
            "GBPUSD": 0.000012,
            "USDJPY": 0.0015,
            "XAUUSD": 0.02,
            "NAS100": 0.8,
            "US30": 1.0,
        }[symbol]
        base_price = {
            "EURUSD": 1.10,
            "GBPUSD": 1.28,
            "USDJPY": 140.0,
            "XAUUSD": 1950.0,
            "NAS100": 15000.0,
            "US30": 35000.0,
        }[symbol]
        hour = timestamps.hour.to_numpy()
        intraday_wave = np.sin(np.arange(n) / 36.0) * symbol_bias * 4
        session_boost = np.where(((hour >= 7) & (hour <= 11)) | ((hour >= 13) & (hour <= 16)), 1.0, 0.2)
        returns = intraday_wave + rng.normal(0, symbol_bias * (1.5 + session_boost), n)
        close = base_price + np.cumsum(returns)
        open_ = np.concatenate(([base_price], close[:-1]))
        high = np.maximum(open_, close) + np.abs(rng.normal(0, symbol_bias * 3, n))
        low = np.minimum(open_, close) - np.abs(rng.normal(0, symbol_bias * 3, n))
        volume = (100 + np.abs(rng.normal(0, 30, n)) * (1 + session_boost)).astype(int)
        return pd.DataFrame(
            {
                "timestamp": timestamps.tz_convert(None),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )
