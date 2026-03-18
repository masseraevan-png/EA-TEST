from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategySpec:
    name: str
    family: str
    description: str
    parameters: dict[str, Any]
    symbols: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)


@dataclass
class BacktestResult:
    strategy_name: str
    trades: int
    net_pnl: float
    profit_factor: float
    max_drawdown: float
    return_to_max_drawdown: float | None = None
    expectancy_per_trade: float | None = None
    notes: str = ""
