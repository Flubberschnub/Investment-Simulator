from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


def decimal_from(value: Any) -> Decimal:
    """Convert API numeric values to Decimal without binary float artifacts."""

    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class Bar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True, slots=True)
class Quote:
    timestamp: datetime
    bid: Decimal
    ask: Decimal

    @property
    def midpoint(self) -> Decimal:
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread_bps(self) -> Decimal:
        midpoint = self.midpoint
        if midpoint <= 0:
            return Decimal("Infinity")
        return ((self.ask - self.bid) / midpoint) * Decimal("10000")


@dataclass(frozen=True, slots=True)
class StrategySignal:
    symbol: str
    timestamp: datetime
    signal_key: str
    entry_estimate: Decimal
    stop_price: Decimal
    target_price: Decimal
    opening_range_high: Decimal
    vwap: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    equity: Decimal
    last_equity: Decimal
    buying_power: Decimal
    trading_blocked: bool

    @property
    def daily_pnl(self) -> Decimal:
        return self.equity - self.last_equity


@dataclass(frozen=True, slots=True)
class MarketClock:
    timestamp: datetime
    is_open: bool
    next_open: datetime
    next_close: datetime


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    symbol: str
    quantity: Decimal
    market_value: Decimal


@dataclass(frozen=True, slots=True)
class OrderSnapshot:
    id: str
    client_order_id: str
    symbol: str
    status: str


@dataclass(frozen=True, slots=True)
class OrderPlan:
    symbol: str
    quantity: int
    entry_estimate: Decimal
    stop_price: Decimal
    target_price: Decimal
    client_order_id: str
    signal_key: str


@dataclass(frozen=True, slots=True)
class RiskDecision:
    allowed: bool
    reason: str
    quantity: int = 0
    risk_budget: Decimal = Decimal("0")
    estimated_notional: Decimal = Decimal("0")
    halt_trading: bool = False


@dataclass(frozen=True, slots=True)
class CycleResult:
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
