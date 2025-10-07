"""Risk management primitives for Craig's momentum bot."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class PositionSizerConfig:
    """Configuration for position sizing and risk controls."""

    account_equity: float = 100_000.0
    risk_fraction: float = 0.01
    atr_multiplier: float = 2.0


class PositionSizer:
    """Calculate share size based on volatility and fixed-fractional risk."""

    def __init__(self, config: PositionSizerConfig | None = None) -> None:
        self.config = config or PositionSizerConfig()

    def size_position(self, entry_price: float, atr: float) -> dict[str, float]:
        if entry_price <= 0:
            raise ValueError("Entry price must be positive")
        if atr <= 0:
            raise ValueError("ATR must be positive")

        risk_capital = self.config.account_equity * self.config.risk_fraction
        stop_price = entry_price - self.config.atr_multiplier * atr
        per_share_risk = entry_price - stop_price

        if per_share_risk <= 0:
            return {"shares": 0, "stop_price": stop_price, "risk_capital": risk_capital}

        shares = floor(risk_capital / per_share_risk)
        exposure = shares * entry_price

        return {
            "shares": shares,
            "stop_price": stop_price,
            "risk_capital": risk_capital,
            "exposure": exposure,
        }
