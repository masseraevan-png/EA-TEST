from __future__ import annotations

import pandas as pd

from ..interfaces import BaseStrategy, SignalEvent, StrategyContext, StrategySpec


class MeanReversionAfterExpansionStrategy(BaseStrategy):
    def __init__(self) -> None:
        self.spec = StrategySpec(
            name="mean_reversion_after_expansion",
            family="mean_reversion_after_expansion",
            hypothesis=(
                "After an outsized intraday expansion, short-term reversion toward the recent mean may "
                "occur during liquid sessions."
            ),
            long_description=(
                "Looks for bars whose range is unusually large versus ATR, then fades the move on the next bar "
                "with ATR-based stop, target, and time stop."
            ),
            parameters={},
        )

    def parameter_grid(self) -> list[dict[str, float | int | str]]:
        return [
            {"expansion_multiple": 1.8, "stop_atr": 0.8, "target_atr": 0.8, "timeout_bars": 6, "direction": "both"},
            {"expansion_multiple": 2.2, "stop_atr": 1.0, "target_atr": 1.2, "timeout_bars": 10, "direction": "both"},
        ]

    def generate_signals(self, bars: pd.DataFrame, context: StrategyContext) -> list[SignalEvent]:
        params = context.parameters
        frame = bars.copy()
        frame["atr"] = (frame["high"] - frame["low"]).rolling(14).mean()
        frame["bar_range"] = frame["high"] - frame["low"]
        frame["bar_move"] = frame["close"] - frame["open"]
        frame["hour"] = frame["timestamp"].dt.hour
        enabled_hours = {7, 8, 9, 10, 11, 13, 14, 15, 16}
        signals: list[SignalEvent] = []
        direction = str(params["direction"])
        for idx in range(20, len(frame) - 1):
            row = frame.iloc[idx]
            if row["hour"] not in enabled_hours or pd.isna(row["atr"]):
                continue
            if row["bar_range"] < float(params["expansion_multiple"]) * row["atr"]:
                continue
            entry = frame.iloc[idx + 1]["open"]
            atr = float(row["atr"])
            if row["bar_move"] > 0 and direction in {"short_only", "both"}:
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=-1,
                        entry_price=float(entry),
                        stop_price=float(entry + float(params["stop_atr"]) * atr),
                        target_price=float(entry - float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "fade_up_expansion"},
                    )
                )
            elif row["bar_move"] < 0 and direction in {"long_only", "both"}:
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=1,
                        entry_price=float(entry),
                        stop_price=float(entry - float(params["stop_atr"]) * atr),
                        target_price=float(entry + float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "fade_down_expansion"},
                    )
                )
        return signals
