from datetime import datetime, timedelta
from decimal import Decimal

from aegis_trader.config import Settings
from aegis_trader.models import Bar
from aegis_trader.simulator import HistoricalSimulator


def test_simulator_uses_conservative_stop_first() -> None:
    start = datetime.fromisoformat("2026-08-03T09:30:00-04:00")
    prices = ["100", "100.1", "100.2", "100.1", "100.15", "100.25", "100.55", "100.55"]
    bars = []
    for i, price in enumerate(prices):
        value = Decimal(price)
        volume = 200 if i == 6 else 100
        high = value + Decimal("0.05")
        low = value - Decimal("0.05")
        if i == 7:
            high = Decimal("101.5")
            low = Decimal("100.0")
        bars.append(Bar(start + timedelta(minutes=5 * i), value, high, low, value, volume))
    report = HistoricalSimulator(Settings(volume_factor=Decimal("1.1"))).run(bars)
    assert len(report.trades) == 1
    assert report.trades[0].exit_reason == "stop"
