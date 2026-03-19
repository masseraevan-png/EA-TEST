from __future__ import annotations

import pandas as pd

from ..interfaces import BaseStrategy, SignalEvent, StrategyContext, StrategySpec


class SessionBreakoutStrategy(BaseStrategy):
    def __init__(self) -> None:
        self.spec = StrategySpec(
            name="session_breakout",
            family="session_breakout",
            hypothesis=(
                "A break of the recent session range during London or New York can continue far "
                "enough to cover conservative costs."
            ),
            long_description=(
                "Uses the prior lookback window high/low as a breakout trigger, requires the trade to be "
                "opened during enabled sessions, and exits using ATR-derived stop, target, or timeout."
            ),
            parameters={},
        )

    def parameter_grid(self) -> list[dict[str, float | int | str]]:
        return [
            {"range_lookback": 12, "breakout_buffer_atr": 0.1, "stop_atr": 1.0, "target_atr": 1.5, "timeout_bars": 12, "direction": "both"},
            {"range_lookback": 18, "breakout_buffer_atr": 0.2, "stop_atr": 1.2, "target_atr": 2.0, "timeout_bars": 18, "direction": "both"},
        ]

    def generate_signals(self, bars: pd.DataFrame, context: StrategyContext) -> list[SignalEvent]:
        params = context.parameters
        frame = bars.copy()
        frame["atr"] = (frame["high"] - frame["low"]).rolling(14).mean()
        frame["hour"] = frame["timestamp"].dt.hour
        frame["prev_high"] = frame["high"].rolling(int(params["range_lookback"])) .max().shift(1)
        frame["prev_low"] = frame["low"].rolling(int(params["range_lookback"])) .min().shift(1)
        enabled_hours = {7, 8, 9, 10, 11, 13, 14, 15, 16}
        signals: list[SignalEvent] = []
        direction = str(params["direction"])
        for idx in range(20, len(frame) - 1):
            row = frame.iloc[idx]
            if row["hour"] not in enabled_hours or pd.isna(row["atr"]):
                continue
            buffer = float(params["breakout_buffer_atr"]) * float(row["atr"])
            if direction in {"long_only", "both"} and row["close"] > row["prev_high"] + buffer:
                entry = frame.iloc[idx + 1]["open"]
                atr = float(row["atr"])
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=1,
                        entry_price=float(entry),
                        stop_price=float(entry - float(params["stop_atr"]) * atr),
                        target_price=float(entry + float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "breakout_long"},
                    )
                )
            if direction in {"short_only", "both"} and row["close"] < row["prev_low"] - buffer:
                entry = frame.iloc[idx + 1]["open"]
                atr = float(row["atr"])
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=-1,
                        entry_price=float(entry),
                        stop_price=float(entry + float(params["stop_atr"]) * atr),
                        target_price=float(entry - float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "breakout_short"},
                    )
                )
        return signals
