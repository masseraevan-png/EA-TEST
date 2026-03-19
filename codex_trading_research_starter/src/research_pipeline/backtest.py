from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ResearchConfig
from .data import MarketDataLoader
from .interfaces import BaseStrategy, SignalEvent, StrategyContext
from .mechanics import SymbolMechanics
from .metrics import PerformanceMetrics, by_year, compute_metrics, monthly_returns


@dataclass
class BacktestArtifacts:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    metrics: PerformanceMetrics
    monthly_returns: pd.DataFrame
    yearly_results: pd.DataFrame
    data_sources: dict[str, str]
    data_quality: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ExecutionOverrides:
    entry_delay_bars: int = 0
    trade_skip_rate: float = 0.0
    adverse_exit_slippage_multiplier: float = 0.0


class BacktestRunner:
    def __init__(self, repo_root: Path, config: ResearchConfig, run_mode: str) -> None:
        self.repo_root = repo_root
        self.config = config
        self.run_mode = run_mode
        self.data_loader = MarketDataLoader(repo_root=repo_root, config=config, run_mode=run_mode)

    def run(
        self,
        strategy: BaseStrategy,
        parameters: dict[str, object],
        symbols: list[str],
        timeframe: str,
        start: str,
        end: str,
        cost_multipliers: tuple[float, float, float] = (1.0, 1.0, 1.0),
        execution_overrides: ExecutionOverrides | None = None,
    ) -> BacktestArtifacts:
        execution_overrides = execution_overrides or ExecutionOverrides()
        requests: list[tuple[str, pd.DataFrame, SignalEvent]] = []
        sources: dict[str, str] = {}
        quality: dict[str, dict[str, Any]] = {}
        for symbol in symbols:
            dataset = self.data_loader.load_symbol(symbol, timeframe)
            sources[symbol] = dataset.source
            quality[symbol] = dataset.quality_summary
            bars = dataset.bars.copy()
            bars["timestamp"] = pd.to_datetime(bars["timestamp"])
            bars = bars[(bars["timestamp"] >= pd.Timestamp(start)) & (bars["timestamp"] <= pd.Timestamp(end))].reset_index(drop=True)
            context = StrategyContext(
                symbol=symbol,
                timeframe=timeframe,
                parameters=parameters,
                session_windows=self.config.raw["sessions"]["definitions"],
            )
            signals = strategy.generate_signals(bars, context)
            for signal in signals:
                requests.append((symbol, bars, signal))
        trades = self._simulate_signals(requests, cost_multipliers, execution_overrides)
        equity_curve = self._build_equity_curve(trades)
        metrics = compute_metrics(trades, equity_curve)
        return BacktestArtifacts(
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics,
            monthly_returns=monthly_returns(trades),
            yearly_results=by_year(trades),
            data_sources=sources,
            data_quality=quality,
        )

    def _simulate_signals(
        self,
        requests: list[tuple[str, pd.DataFrame, SignalEvent]],
        cost_multipliers: tuple[float, float, float],
        execution_overrides: ExecutionOverrides,
    ) -> pd.DataFrame:
        if not requests:
            return pd.DataFrame(columns=["symbol", "entry_time", "exit_time", "side", "entry_price", "exit_price", "pnl", "r_multiple", "exit_reason"])
        rows: list[dict[str, object]] = []
        spread_mult, slip_mult, commission_mult = cost_multipliers
        equity = self.config.initial_equity_usd
        requests = sorted(requests, key=lambda item: item[2].timestamp)
        bars_lookup_cache: dict[str, dict[pd.Timestamp, int]] = {}
        for symbol, bars, signal in requests:
            cost_spec = self.config.cost_for_symbol(symbol)
            mechanics = self.config.mechanics_for_symbol(symbol)
            bars_by_time = bars_lookup_cache.setdefault(
                symbol, {ts: idx for idx, ts in enumerate(bars["timestamp"])}
            )
            start_idx = bars_by_time.get(signal.timestamp)
            if start_idx is None:
                continue
            if self._skip_trade(symbol, signal, execution_overrides.trade_skip_rate):
                continue
            start_idx = start_idx + execution_overrides.entry_delay_bars
            if start_idx >= len(bars):
                continue
            entry_price = float(bars.iloc[start_idx]["open"])
            stop_distance = abs(signal.entry_price - signal.stop_price)
            target_distance = abs(signal.target_price - signal.entry_price)
            if signal.side == 1:
                stop_price = entry_price - stop_distance
                target_price = entry_price + target_distance
            else:
                stop_price = entry_price + stop_distance
                target_price = entry_price - target_distance
            risk_amount_usd = equity * self.config.risk_per_trade
            position_size = mechanics.size_for_risk(
                risk_amount_usd=risk_amount_usd,
                stop_distance_price=stop_distance,
                reference_price=entry_price,
            )
            if position_size <= 0:
                continue
            spread_cost_usd = self._cost_component_to_usd(
                mechanics,
                cost_spec.spread_unit,
                cost_spec.spread_value * spread_mult,
                reference_price=entry_price,
            ) * position_size
            slippage_cost_usd = self._cost_component_to_usd(
                mechanics,
                cost_spec.slippage_unit,
                cost_spec.slippage_value * slip_mult,
                reference_price=entry_price,
            ) * position_size
            per_trade_cost = (
                spread_cost_usd
                + slippage_cost_usd
                + cost_spec.commission_round_turn_usd_per_lot * commission_mult * position_size
            )
            exit_price = bars.iloc[min(start_idx + signal.timeout_bars, len(bars) - 1)]["close"]
            exit_time = bars.iloc[min(start_idx + signal.timeout_bars, len(bars) - 1)]["timestamp"]
            exit_reason = "timeout"
            for idx in range(start_idx, min(start_idx + signal.timeout_bars + 1, len(bars))):
                row = bars.iloc[idx]
                if signal.side == 1:
                    stop_hit = row["low"] <= stop_price
                    target_hit = row["high"] >= target_price
                    if stop_hit and target_hit:
                        exit_price = stop_price
                        exit_time = row["timestamp"]
                        exit_reason = "stop_priority_same_bar"
                        break
                    if stop_hit:
                        exit_price = stop_price
                        exit_time = row["timestamp"]
                        exit_reason = "stop"
                        break
                    if target_hit:
                        exit_price = target_price
                        exit_time = row["timestamp"]
                        exit_reason = "target"
                        break
                else:
                    stop_hit = row["high"] >= stop_price
                    target_hit = row["low"] <= target_price
                    if stop_hit and target_hit:
                        exit_price = stop_price
                        exit_time = row["timestamp"]
                        exit_reason = "stop_priority_same_bar"
                        break
                    if stop_hit:
                        exit_price = stop_price
                        exit_time = row["timestamp"]
                        exit_reason = "stop"
                        break
                    if target_hit:
                        exit_price = target_price
                        exit_time = row["timestamp"]
                        exit_reason = "target"
                        break
            if execution_overrides.adverse_exit_slippage_multiplier > 0 and exit_reason in {
                "stop_priority_same_bar",
                "stop",
                "target",
            }:
                exit_price = self._apply_adverse_exit_price(
                    symbol=symbol,
                    side=signal.side,
                    exit_reason=exit_reason,
                    exit_price=float(exit_price),
                    mechanics=mechanics,
                    cost_spec=cost_spec,
                    multiplier=execution_overrides.adverse_exit_slippage_multiplier,
                )
            gross_price_move = (exit_price - entry_price) * signal.side
            gross = mechanics.price_move_to_usd_pnl(
                gross_price_move,
                reference_price=float(exit_price),
                lots=position_size,
            )
            risk = mechanics.price_move_to_usd_pnl(
                stop_distance,
                reference_price=entry_price,
                lots=position_size,
            ) or 1e-9
            pnl = gross - per_trade_cost
            equity_after = equity + pnl
            rows.append(
                {
                    "symbol": symbol,
                    "entry_time": signal.timestamp,
                    "exit_time": exit_time,
                    "side": signal.side,
                    "entry_price": entry_price,
                    "exit_price": float(exit_price),
                    "equity_before": float(equity),
                    "equity_after": float(equity_after),
                    "risk_amount_usd": float(risk_amount_usd),
                    "position_size": float(position_size),
                    "intended_risk_pct": float(self.config.risk_per_trade),
                    "gross_pnl_usd": float(gross),
                    "spread_cost_usd": float(spread_cost_usd),
                    "slippage_cost_usd": float(slippage_cost_usd),
                    "commission_cost_usd": float(
                        cost_spec.commission_round_turn_usd_per_lot * commission_mult * position_size
                    ),
                    "pnl": float(pnl),
                    "r_multiple": float(pnl / risk),
                    "exit_reason": exit_reason,
                }
            )
            equity = equity_after
        trades = pd.DataFrame(rows)
        return trades.sort_values("exit_time").reset_index(drop=True) if not trades.empty else trades

    @staticmethod
    def _cost_component_to_usd(
        mechanics: SymbolMechanics,
        unit: str,
        value: float,
        reference_price: float,
    ) -> float:
        price_move = mechanics.cost_unit_to_price_move(unit, value)
        return mechanics.price_move_to_usd_pnl(
            price_move,
            reference_price=reference_price,
        )

    @staticmethod
    def _skip_trade(symbol: str, signal: SignalEvent, trade_skip_rate: float) -> bool:
        if trade_skip_rate <= 0:
            return False
        deterministic_bucket = ((signal.timestamp.value // 10**9) + sum(ord(ch) for ch in symbol)) % 1000
        return deterministic_bucket / 1000.0 < trade_skip_rate

    @staticmethod
    def _apply_adverse_exit_price(
        symbol: str,
        side: int,
        exit_reason: str,
        exit_price: float,
        mechanics: SymbolMechanics,
        cost_spec,
        multiplier: float,
    ) -> float:
        adverse_move = mechanics.cost_unit_to_price_move(
            cost_spec.slippage_unit,
            cost_spec.slippage_value * multiplier,
        )
        if side == 1:
            return exit_price - adverse_move
        return exit_price + adverse_move

    @staticmethod
    def _build_equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
        if trades.empty:
            return pd.DataFrame(columns=["timestamp", "equity", "drawdown"])
        curve = trades[["exit_time", "equity_after"]].copy().rename(columns={"exit_time": "timestamp", "equity_after": "equity"})
        starting_row = pd.DataFrame(
            [{"timestamp": trades.iloc[0]["entry_time"], "equity": float(trades.iloc[0]["equity_before"])}]
        )
        curve = pd.concat([starting_row, curve], ignore_index=True)
        curve["peak"] = curve["equity"].cummax()
        curve["drawdown"] = curve["peak"] - curve["equity"]
        return curve[["timestamp", "equity", "drawdown"]]
