from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class StrategySpec:
    name: str
    family: str
    hypothesis: str
    long_description: str
    parameters: dict[str, Any]
    symbols: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SignalEvent:
    timestamp: pd.Timestamp
    side: int
    entry_price: float
    stop_price: float
    target_price: float
    timeout_bars: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyContext:
    symbol: str
    timeframe: str
    parameters: dict[str, Any]
    session_windows: dict[str, dict[str, str]]


class BaseStrategy:
    """Strategy interface for interpretable bar-based intraday systems."""

    spec: StrategySpec

    def parameter_grid(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def generate_signals(self, bars: pd.DataFrame, context: StrategyContext) -> list[SignalEvent]:
        raise NotImplementedError
