from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from aegis_trader.config import Settings
from aegis_trader.models import BacktestReport, Bar, Trade
from aegis_trader.risk import RiskGateway
from aegis_trader.strategy import OpeningRangeBreakout


def load_bars(path: Path) -> list[Bar]:
    bars: list[Bar] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            bars.append(
                Bar(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=int(row["volume"]),
                )
            )
    return sorted(bars, key=lambda bar: bar.timestamp)


class HistoricalSimulator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.strategy = OpeningRangeBreakout(settings)
        self.risk = RiskGateway(settings)

    def run(self, bars: list[Bar]) -> BacktestReport:
        cash = self.settings.starting_cash
        report = BacktestReport(starting_cash=cash, ending_cash=cash)
        by_day: dict[object, list[Bar]] = {}
        for bar in bars:
            by_day.setdefault(bar.timestamp.date(), []).append(bar)

        for day_bars in by_day.values():
            day_pnl = Decimal("0")
            trades_today = 0
            for index in range(3, len(day_bars) - 1):
                signal = self.strategy.evaluate(day_bars[: index + 1])
                if signal is None:
                    continue
                decision = self.risk.size_trade(
                    equity=cash,
                    entry=signal.entry,
                    stop=signal.stop,
                    day_pnl=day_pnl,
                    trades_today=trades_today,
                )
                if not decision.allowed:
                    break

                exit_bar = day_bars[-1]
                exit_price = exit_bar.close
                exit_reason = "end_of_day"
                for candidate in day_bars[index + 1 :]:
                    if candidate.low <= signal.stop:
                        exit_bar = candidate
                        exit_price = signal.stop
                        exit_reason = "stop"
                        break
                    if candidate.high >= signal.target:
                        exit_bar = candidate
                        exit_price = signal.target
                        exit_reason = "target"
                        break

                pnl = (exit_price - signal.entry) * decision.quantity
                report.trades.append(
                    Trade(
                        symbol=signal.symbol,
                        entry_time=signal.timestamp,
                        exit_time=exit_bar.timestamp,
                        quantity=decision.quantity,
                        entry=signal.entry,
                        exit=exit_price,
                        stop=signal.stop,
                        target=signal.target,
                        pnl=pnl,
                        exit_reason=exit_reason,
                    )
                )
                cash += pnl
                day_pnl += pnl
                trades_today += 1
                break
        report.ending_cash = cash
        return report
