from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .mechanics import SymbolMechanics


class ConfigError(ValueError):
    """Raised when the research configuration is invalid."""


@dataclass(frozen=True)
class CostSpec:
    symbol: str
    asset_class: str
    base_currency: str
    quote_currency: str
    contract_size: float
    min_position_size: float
    position_size_step: float
    max_position_size: float | None
    price_increment: float
    pip_size: float | None
    spread_value: float
    spread_unit: str
    slippage_value: float
    slippage_unit: str
    commission_round_turn_usd_per_lot: float


class ResearchConfig:
    """Thin wrapper around the YAML config with strict validation helpers."""

    def __init__(self, raw: dict[str, Any], path: Path) -> None:
        self.raw = raw
        self.path = path
        self._validate()

    def _validate(self) -> None:
        required_sections = [
            "project",
            "runtime",
            "universe",
            "sessions",
            "risk_model",
            "execution",
            "data",
            "costs",
            "filters",
            "walk_forward",
            "stress_tests",
            "metrics",
            "reporting",
        ]
        missing = [section for section in required_sections if section not in self.raw]
        if missing:
            raise ConfigError(f"Missing required config sections: {missing}")

        symbols = self.symbols
        explicit_costs = self.raw["costs"].get("symbols", {})
        missing_costs = [symbol for symbol in symbols if symbol not in explicit_costs]
        if missing_costs:
            raise ConfigError(
                "Missing explicit symbol-specific cost entries for active universe symbols: "
                f"{missing_costs}"
            )

        split = self.raw["data"].get("split", {})
        split_keys = [
            "train_start",
            "train_end",
            "validation_start",
            "validation_end",
            "test_start",
            "test_end",
            "holdout_start",
            "holdout_end",
        ]
        if any(key not in split for key in split_keys):
            raise ConfigError("Data split is incomplete in configs/base_config.yaml")

        risk_model = self.raw["risk_model"]
        if "initial_equity_usd" not in risk_model:
            raise ConfigError("risk_model.initial_equity_usd is required for equity-aware sizing")

        required_symbol_fields = {
            "asset_class",
            "base_currency",
            "quote_currency",
            "contract_size",
            "min_position_size",
            "position_size_step",
            "price_increment",
            "spread_value",
            "spread_unit",
            "slippage_value",
            "slippage_unit",
            "commission_round_turn_usd_per_lot",
        }
        for symbol in symbols:
            symbol_cost = explicit_costs[symbol]
            missing_fields = sorted(required_symbol_fields - set(symbol_cost))
            if missing_fields:
                raise ConfigError(
                    f"Symbol mechanics/cost metadata missing for {symbol}: {missing_fields}"
                )
            if symbol_cost["spread_unit"] == "pips" and symbol_cost.get("pip_size") is None:
                raise ConfigError(f"{symbol} uses pip-based costs but has no pip_size configured")
            if float(symbol_cost["position_size_step"]) <= 0:
                raise ConfigError(f"{symbol} must have a positive position_size_step")
            if float(symbol_cost["min_position_size"]) <= 0:
                raise ConfigError(f"{symbol} must have a positive min_position_size")

    @property
    def symbols(self) -> list[str]:
        return list(self.raw["universe"]["symbols"])

    @property
    def timeframes(self) -> list[str]:
        return list(self.raw["universe"]["primary_timeframes"])

    @property
    def default_timeframe(self) -> str:
        return str(self.raw["universe"]["default_timeframe"])

    @property
    def split(self) -> dict[str, str]:
        return dict(self.raw["data"]["split"])

    @property
    def reporting(self) -> dict[str, Any]:
        return dict(self.raw["reporting"])

    @property
    def initial_equity_usd(self) -> float:
        return float(self.raw["risk_model"]["initial_equity_usd"])

    @property
    def risk_per_trade(self) -> float:
        return float(self.raw["risk_model"]["risk_per_trade"])

    @property
    def default_run_mode(self) -> str:
        run_mode = str(self.raw["runtime"]["default_run_mode"])
        allowed = set(self.raw["runtime"].get("allowed_run_modes", []))
        if run_mode not in allowed:
            raise ConfigError(f"Unsupported default run mode in config: {run_mode}")
        return run_mode

    def resolve_run_mode(self, requested_mode: str | None) -> str:
        run_mode = requested_mode or self.default_run_mode
        allowed = set(self.raw["runtime"].get("allowed_run_modes", []))
        if run_mode not in allowed:
            raise ConfigError(
                f"Unsupported run mode '{run_mode}'. Allowed modes: {sorted(allowed)}"
            )
        return run_mode

    def cost_for_symbol(self, symbol: str) -> CostSpec:
        symbol_cost = self.raw["costs"]["symbols"].get(symbol)
        if symbol_cost is None:
            raise ConfigError(
                f"No explicit cost entry configured for {symbol}. "
                "Default placeholder costs must never be used for active symbols."
            )
        return CostSpec(
            symbol=symbol,
            asset_class=str(symbol_cost["asset_class"]),
            base_currency=str(symbol_cost["base_currency"]),
            quote_currency=str(symbol_cost["quote_currency"]),
            contract_size=float(symbol_cost["contract_size"]),
            min_position_size=float(symbol_cost["min_position_size"]),
            position_size_step=float(symbol_cost["position_size_step"]),
            max_position_size=float(symbol_cost["max_position_size"]) if symbol_cost.get("max_position_size") is not None else None,
            price_increment=float(symbol_cost["price_increment"]),
            pip_size=float(symbol_cost["pip_size"]) if symbol_cost.get("pip_size") is not None else None,
            spread_value=float(symbol_cost["spread_value"]),
            spread_unit=str(symbol_cost["spread_unit"]),
            slippage_value=float(symbol_cost["slippage_value"]),
            slippage_unit=str(symbol_cost["slippage_unit"]),
            commission_round_turn_usd_per_lot=float(
                symbol_cost["commission_round_turn_usd_per_lot"]
            ),
        )

    def mechanics_for_symbol(self, symbol: str) -> SymbolMechanics:
        cost = self.cost_for_symbol(symbol)
        return SymbolMechanics(
            symbol=cost.symbol,
            asset_class=cost.asset_class,
            base_currency=cost.base_currency,
            quote_currency=cost.quote_currency,
            contract_size=cost.contract_size,
            min_position_size=cost.min_position_size,
            position_size_step=cost.position_size_step,
            max_position_size=cost.max_position_size,
            price_increment=cost.price_increment,
            pip_size=cost.pip_size,
        )


def load_config(path: str | Path) -> ResearchConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return ResearchConfig(raw=raw, path=config_path)
