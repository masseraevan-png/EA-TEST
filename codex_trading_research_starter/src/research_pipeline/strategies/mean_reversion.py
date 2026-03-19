from __future__ import annotations

import pandas as pd

from ..interfaces import BaseStrategy, SignalEvent, StrategyContext, StrategySpec


ENABLED_HOURS = {7, 8, 9, 10, 11, 13, 14, 15, 16}


def _base_mean_reversion_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["atr"] = (frame["high"] - frame["low"]).rolling(14).mean()
    frame["bar_range"] = frame["high"] - frame["low"]
    frame["bar_move"] = frame["close"] - frame["open"]
    frame["hour"] = frame["timestamp"].dt.hour
    return frame


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
        frame = _base_mean_reversion_frame(bars)
        signals: list[SignalEvent] = []
        direction = str(params["direction"])
        for idx in range(20, len(frame) - 1):
            row = frame.iloc[idx]
            if row["hour"] not in ENABLED_HOURS or pd.isna(row["atr"]):
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


class MeanReversionExhaustionWickStrategy(BaseStrategy):
    def __init__(self) -> None:
        self.spec = StrategySpec(
            name="mean_reversion_exhaustion_wick",
            family="mean_reversion_after_expansion",
            hypothesis=(
                "Fade only the largest expansion bars that also show same-bar exhaustion via a long rejection wick "
                "and a weak close."
            ),
            long_description=(
                "Requires an outsized ATR-relative expansion plus a close back away from the extreme, aiming to "
                "trade fewer but more exhausted reversal setups."
            ),
            parameters={},
        )

    def parameter_grid(self) -> list[dict[str, float | int | str]]:
        return [
            {
                "expansion_multiple": 2.4,
                "close_reversal_fraction": 0.35,
                "wick_fraction": 0.30,
                "stop_atr": 1.0,
                "target_atr": 1.4,
                "timeout_bars": 8,
                "direction": "both",
            }
        ]

    def generate_signals(self, bars: pd.DataFrame, context: StrategyContext) -> list[SignalEvent]:
        params = context.parameters
        frame = _base_mean_reversion_frame(bars)
        signals: list[SignalEvent] = []
        direction = str(params["direction"])
        for idx in range(20, len(frame) - 1):
            row = frame.iloc[idx]
            if row["hour"] not in ENABLED_HOURS or pd.isna(row["atr"]) or row["bar_range"] <= 0:
                continue
            if row["bar_range"] < float(params["expansion_multiple"]) * row["atr"]:
                continue
            close_in_range = (row["close"] - row["low"]) / row["bar_range"]
            upper_wick_fraction = (row["high"] - max(row["open"], row["close"])) / row["bar_range"]
            lower_wick_fraction = (min(row["open"], row["close"]) - row["low"]) / row["bar_range"]
            entry = frame.iloc[idx + 1]["open"]
            atr = float(row["atr"])
            if (
                row["bar_move"] > 0
                and direction in {"short_only", "both"}
                and close_in_range <= float(params["close_reversal_fraction"])
                and upper_wick_fraction >= float(params["wick_fraction"])
            ):
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=-1,
                        entry_price=float(entry),
                        stop_price=float(entry + float(params["stop_atr"]) * atr),
                        target_price=float(entry - float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "exhaustion_wick_short"},
                    )
                )
            elif (
                row["bar_move"] < 0
                and direction in {"long_only", "both"}
                and close_in_range >= 1.0 - float(params["close_reversal_fraction"])
                and lower_wick_fraction >= float(params["wick_fraction"])
            ):
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 1]["timestamp"],
                        side=1,
                        entry_price=float(entry),
                        stop_price=float(entry - float(params["stop_atr"]) * atr),
                        target_price=float(entry + float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "exhaustion_wick_long"},
                    )
                )
        return signals


class MeanReversionFailedFollowThroughStrategy(BaseStrategy):
    def __init__(self) -> None:
        self.spec = StrategySpec(
            name="mean_reversion_failed_follow_through",
            family="mean_reversion_after_expansion",
            hypothesis=(
                "Fade only after an outsized expansion bar is followed by a failed continuation bar that closes "
                "back toward the middle of the impulse."
            ),
            long_description=(
                "Waits for one-bar confirmation that follow-through is failing before fading the move, which should "
                "reduce marginal trades and improve edge per trade."
            ),
            parameters={},
        )

    def parameter_grid(self) -> list[dict[str, float | int | str]]:
        return [
            {
                "expansion_multiple": 2.2,
                "confirm_retrace_fraction": 0.45,
                "stop_atr": 1.0,
                "target_atr": 1.3,
                "timeout_bars": 8,
                "direction": "both",
            }
        ]

    def generate_signals(self, bars: pd.DataFrame, context: StrategyContext) -> list[SignalEvent]:
        params = context.parameters
        frame = _base_mean_reversion_frame(bars)
        signals: list[SignalEvent] = []
        direction = str(params["direction"])
        for idx in range(20, len(frame) - 2):
            impulse = frame.iloc[idx]
            confirm = frame.iloc[idx + 1]
            if impulse["hour"] not in ENABLED_HOURS or pd.isna(impulse["atr"]) or impulse["bar_range"] <= 0:
                continue
            if impulse["bar_range"] < float(params["expansion_multiple"]) * impulse["atr"]:
                continue
            retrace_level = float(params["confirm_retrace_fraction"])
            impulse_mid = impulse["low"] + retrace_level * impulse["bar_range"]
            entry = frame.iloc[idx + 2]["open"]
            atr = float(impulse["atr"])
            if (
                impulse["bar_move"] > 0
                and direction in {"short_only", "both"}
                and confirm["close"] < impulse_mid
                and confirm["high"] <= impulse["high"]
            ):
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 2]["timestamp"],
                        side=-1,
                        entry_price=float(entry),
                        stop_price=float(entry + float(params["stop_atr"]) * atr),
                        target_price=float(entry - float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "failed_follow_through_short"},
                    )
                )
            elif (
                impulse["bar_move"] < 0
                and direction in {"long_only", "both"}
                and confirm["close"] > impulse_mid
                and confirm["low"] >= impulse["low"]
            ):
                signals.append(
                    SignalEvent(
                        timestamp=frame.iloc[idx + 2]["timestamp"],
                        side=1,
                        entry_price=float(entry),
                        stop_price=float(entry - float(params["stop_atr"]) * atr),
                        target_price=float(entry + float(params["target_atr"]) * atr),
                        timeout_bars=int(params["timeout_bars"]),
                        metadata={"reason": "failed_follow_through_long"},
                    )
                )
        return signals
