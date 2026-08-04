from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True)
class Signal:
    timestamp: datetime
    symbol: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    reason: str


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    quantity: int = 0
    reason: str = ""


@dataclass(frozen=True)
class Trade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    quantity: int
    entry: Decimal
    exit: Decimal
    stop: Decimal
    target: Decimal
    pnl: Decimal
    exit_reason: str


@dataclass
class BacktestReport:
    starting_cash: Decimal
    ending_cash: Decimal
    trades: list[Trade] = field(default_factory=list)

    @property
    def total_pnl(self) -> Decimal:
        return self.ending_cash - self.starting_cash

    @property
    def win_rate(self) -> Decimal:
        if not self.trades:
            return Decimal("0")
        wins = sum(1 for trade in self.trades if trade.pnl > 0)
        return Decimal(wins) / Decimal(len(self.trades))

    def as_dict(self) -> dict[str, Any]:
        return {
            "starting_cash": str(self.starting_cash),
            "ending_cash": str(self.ending_cash),
            "total_pnl": str(self.total_pnl),
            "trades": len(self.trades),
            "win_rate": str(self.win_rate),
        }
