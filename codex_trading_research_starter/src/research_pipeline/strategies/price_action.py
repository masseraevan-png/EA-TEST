from __future__ import annotations

import pandas as pd

from ..interfaces import BaseStrategy, SignalEvent, StrategyContext, StrategySpec

ENABLED_HOURS = {7, 8, 9, 10, 11, 13, 14, 15, 16}
ASIA_END_HOUR = 6


def _base_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame["atr"] = (frame["high"] - frame["low"]).rolling(14).mean()
    frame["bar_range"] = frame["high"] - frame["low"]
    frame["bar_body"] = (frame["close"] - frame["open"]).abs()
    frame["hour"] = frame["timestamp"].dt.hour
    frame["date"] = frame["timestamp"].dt.floor("D")

    asia_highs: list[float] = []
    asia_lows: list[float] = []
    current_date = None
    running_high = float("nan")
    running_low = float("nan")
    for row in frame.itertuples():
        if row.date != current_date:
            current_date = row.date
            running_high = float("nan")
            running_low = float("nan")
        asia_highs.append(running_high)
        asia_lows.append(running_low)
        if row.hour <= ASIA_END_HOUR:
            running_high = row.high if pd.isna(running_high) else max(running_high, row.high)
            running_low = row.low if pd.isna(running_low) else min(running_low, row.low)

    frame["asia_high"] = asia_highs
    frame["asia_low"] = asia_lows
    frame["asia_range"] = frame["asia_high"] - frame["asia_low"]
    return frame


class LiquiditySweepReversalStrategy(BaseStrategy):
    def __init__(self) -> None:
        self.spec = StrategySpec(
            name="liquidity_sweep_reversal",
            family="liquidity_sweep_failed_break",
            hypothesis=(
                "When London or New York briefly sweeps the Asian session extreme and closes back inside the "
                "range, the failed break can reverse toward internal liquidity with fewer but higher-quality trades."
            ),
            long_description=(
                "Tracks completed Asian-session highs and lows, looks for a sweep beyond that liquidity followed by "
                "a rejection close back inside the range, and enters next bar in the reversal direction with ATR-"
                "anchored stop and target."
            ),
            parameters={},
        )

    def parameter_grid(self) -> list[dict[str, float | int | str]]:
        return [
            {
                "min_sweep_atr": 0.12,
                "min_reentry_fraction": 0.15,
                "min_wick_fraction": 0.35,
                "stop_atr": 0.9,
                "target_atr": 1.8,
                "timeout_bars": 16,
                "direction": "both",
            },
            {
                "min_sweep_atr": 0.18,
                "min_reentry_fraction": 0.20,
                "min_wick_fraction": 0.40,
                "stop_atr": 1.0,
                "target_atr": 2.0,
                "timeout_bars": 20,
                "direction": "both",
            },
        ]

    def generate_signals(self, bars: pd.DataFrame, context: StrategyContext) -> list[SignalEvent]:
        params = context.parameters
        frame = _base_frame(bars)
        signals: list[SignalEvent] = []
        direction = str(params["direction"])
        for idx in range(20, len(frame) - 1):
            row = frame.iloc[idx]
            if row["hour"] not in ENABLED_HOURS or pd.isna(row["atr"]) or pd.isna(row["asia_high"]) or row["bar_range"] <= 0:
                continue
            min_sweep = float(params["min_sweep_atr"]) * float(row["atr"])
            if row["asia_range"] <= 0:
                continue
            close_in_range = (row["close"] - row["low"]) / row["bar_range"]
            upper_wick = (row["high"] - max(row["open"], row["close"])) / row["bar_range"]
            lower_wick = (min(row["open"], row["close"]) - row["low"]) / row["bar_range"]
            entry = float(frame.iloc[idx + 1]["open"])
            atr = float(row["atr"])

            swept_above = row["high"] >= row["asia_high"] + min_sweep and row["close"] < row["asia_high"] - float(params["min_reentry_fraction"]) * row["asia_range"]
            swept_below = row["low"] <= row["asia_low"] - min_sweep and row["close"] > row["asia_low"] + float(params["min_reentry_fraction"]) * row["asia_range"]

            if swept_above and upper_wick >= float(params["min_wick_fraction"]) and direction in {"short_only", "both"}:
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=-1,
                        entry_price=entry,
                        stop_price=float(entry + float(params["stop_atr"]) * atr),
                        target_price=float(entry - float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "asia_high_sweep_reversal_short"},
                    )
                )
            elif swept_below and lower_wick >= float(params["min_wick_fraction"]) and direction in {"long_only", "both"}:
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=1,
                        entry_price=entry,
                        stop_price=float(entry - float(params["stop_atr"]) * atr),
                        target_price=float(entry + float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "asia_low_sweep_reversal_long"},
                    )
                )
        return signals


class OpeningDrivePullbackStrategy(BaseStrategy):
    def __init__(self) -> None:
        self.spec = StrategySpec(
            name="opening_drive_pullback",
            family="pullback_continuation",
            hypothesis=(
                "A genuine London/New York opening drive that breaks the Asian range and then pulls back shallowly "
                "often continues, offering fewer trades with better per-trade payoff than broad breakout chasing."
            ),
            long_description=(
                "Requires an impulse bar that breaks the Asian range with an ATR-sized body, then a single-bar pullback "
                "that stays above or below the broken level before entering continuation on the next bar."
            ),
            parameters={},
        )

    def parameter_grid(self) -> list[dict[str, float | int | str]]:
        return [
            {
                "impulse_body_atr": 0.9,
                "break_buffer_atr": 0.10,
                "max_pullback_fraction": 0.45,
                "stop_atr": 1.0,
                "target_atr": 1.8,
                "timeout_bars": 20,
                "direction": "both",
            },
            {
                "impulse_body_atr": 1.1,
                "break_buffer_atr": 0.15,
                "max_pullback_fraction": 0.40,
                "stop_atr": 1.1,
                "target_atr": 2.1,
                "timeout_bars": 24,
                "direction": "both",
            },
        ]

    def generate_signals(self, bars: pd.DataFrame, context: StrategyContext) -> list[SignalEvent]:
        params = context.parameters
        frame = _base_frame(bars)
        signals: list[SignalEvent] = []
        direction = str(params["direction"])
        for idx in range(20, len(frame) - 2):
            impulse = frame.iloc[idx]
            pullback = frame.iloc[idx + 1]
            if (
                impulse["hour"] not in ENABLED_HOURS
                or pd.isna(impulse["atr"])
                or pd.isna(impulse["asia_high"])
                or impulse["bar_range"] <= 0
            ):
                continue
            atr = float(impulse["atr"])
            body = abs(float(impulse["close"] - impulse["open"]))
            if body < float(params["impulse_body_atr"]) * atr:
                continue
            entry = float(frame.iloc[idx + 2]["open"])
            break_buffer = float(params["break_buffer_atr"]) * atr
            max_pullback = float(params["max_pullback_fraction"]) * max(body, 1e-9)
            broken_high = float(impulse["asia_high"])
            broken_low = float(impulse["asia_low"])

            if (
                impulse["close"] > broken_high + break_buffer
                and direction in {"long_only", "both"}
                and pullback["low"] >= broken_high - break_buffer
                and pullback["close"] >= broken_high
                and (impulse["close"] - pullback["low"]) <= max_pullback
            ):
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 2]["timestamp"],
                        side=1,
                        entry_price=entry,
                        stop_price=float(entry - float(params["stop_atr"]) * atr),
                        target_price=float(entry + float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "opening_drive_pullback_long"},
                    )
                )
            elif (
                impulse["close"] < broken_low - break_buffer
                and direction in {"short_only", "both"}
                and pullback["high"] <= broken_low + break_buffer
                and pullback["close"] <= broken_low
                and (pullback["high"] - impulse["close"]) <= max_pullback
            ):
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 2]["timestamp"],
                        side=-1,
                        entry_price=entry,
                        stop_price=float(entry + float(params["stop_atr"]) * atr),
                        target_price=float(entry - float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "opening_drive_pullback_short"},
                    )
                )
        return signals
