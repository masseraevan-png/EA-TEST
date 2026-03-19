from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SymbolMechanics:
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

    def price_move_to_usd_pnl(
        self,
        price_move: float,
        reference_price: float,
        lots: float = 1.0,
    ) -> float:
        quote_pnl = price_move * self.contract_size * lots
        if self.asset_class in {"metal", "index_cfd"} or self.quote_currency == "USD":
            return quote_pnl
        if self.asset_class == "fx" and self.quote_currency == "JPY":
            if reference_price <= 0:
                raise ValueError(
                    f"{self.symbol} requires a positive reference price for JPY->USD conversion."
                )
            return quote_pnl / reference_price
        raise ValueError(
            f"{self.symbol} uses unsupported asset_class/quote conversion: "
            f"{self.asset_class}/{self.quote_currency}"
        )

    def cost_unit_to_price_move(self, unit: str, value: float) -> float:
        if unit == "pips":
            if self.pip_size is None:
                raise ValueError(f"{self.symbol} has no pip_size but received pip-based costs.")
            return value * self.pip_size
        if unit == "usd":
            if self.quote_currency != "USD":
                raise ValueError(f"{self.symbol} cannot use usd move costs without USD quote currency.")
            return value
        if unit == "index_points":
            return value
        raise ValueError(f"{self.symbol} has unsupported cost unit: {unit}")

    def describe(self) -> str:
        pip_text = f", pip_size={self.pip_size}" if self.pip_size is not None else ""
        return (
            f"asset_class={self.asset_class}, base={self.base_currency}, quote={self.quote_currency}, "
            f"contract_size={self.contract_size}, min_size={self.min_position_size}, "
            f"size_step={self.position_size_step}, max_size={self.max_position_size}, "
            f"price_increment={self.price_increment}{pip_text}"
        )

    def size_for_risk(self, risk_amount_usd: float, stop_distance_price: float, reference_price: float) -> float:
        risk_per_unit = self.price_move_to_usd_pnl(abs(stop_distance_price), reference_price, lots=1.0)
        if risk_per_unit <= 0:
            raise ValueError(f"{self.symbol} produced non-positive risk_per_unit during sizing.")
        raw_size = risk_amount_usd / risk_per_unit
        stepped_size = math.floor(raw_size / self.position_size_step) * self.position_size_step
        if self.max_position_size is not None:
            stepped_size = min(stepped_size, self.max_position_size)
        if stepped_size < self.min_position_size:
            return 0.0
        return round(stepped_size, 8)
