from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from aegis_trader.config import Settings
from aegis_trader.models import Bar
from aegis_trader.strategy import OpeningRangeBreakoutStrategy

ET = ZoneInfo("America/New_York")


def bar(minute: int, *, close: str, high: str, low: str, volume: int) -> Bar:
    timestamp = datetime(2026, 8, 3, 9, 30, tzinfo=ET) + timedelta(minutes=minute)
    close_value = Decimal(close)
    return Bar(
        timestamp=timestamp,
        open=close_value,
        high=Decimal(high),
        low=Decimal(low),
        close=close_value,
        volume=volume,
    )


def test_generates_breakout_signal() -> None:
    settings = Settings(volume_factor=Decimal("1.10"), max_extension_pct=Decimal("0.01"))
    strategy = OpeningRangeBreakoutStrategy(settings)
    bars = [
        bar(0, close="100.00", high="100.20", low="99.80", volume=100),
        bar(5, close="100.10", high="100.30", low="99.95", volume=100),
        bar(10, close="100.15", high="100.40", low="100.00", volume=100),
        bar(15, close="100.20", high="100.30", low="100.05", volume=100),
        bar(20, close="100.25", high="100.35", low="100.10", volume=100),
        bar(25, close="100.30", high="100.36", low="100.15", volume=100),
        bar(30, close="100.32", high="100.38", low="100.20", volume=100),
        bar(35, close="100.35", high="100.39", low="100.25", volume=100),
        bar(40, close="100.65", high="100.70", low="100.34", volume=150),
    ]

    signal = strategy.evaluate(bars, datetime(2026, 8, 3, 10, 16, tzinfo=ET))

    assert signal is not None
    assert signal.entry_estimate == Decimal("100.65")
    assert signal.stop_price == Decimal("100.34")
    assert signal.target_price == Decimal("101.27")


def test_rejects_unconfirmed_volume() -> None:
    settings = Settings(volume_factor=Decimal("1.50"), max_extension_pct=Decimal("0.01"))
    strategy = OpeningRangeBreakoutStrategy(settings)
    bars = [
        bar(0, close="100.00", high="100.20", low="99.80", volume=100),
        bar(5, close="100.10", high="100.30", low="99.95", volume=100),
        bar(10, close="100.15", high="100.40", low="100.00", volume=100),
        bar(15, close="100.20", high="100.30", low="100.05", volume=100),
        bar(20, close="100.25", high="100.35", low="100.10", volume=100),
        bar(25, close="100.30", high="100.36", low="100.15", volume=100),
        bar(30, close="100.32", high="100.38", low="100.20", volume=100),
        bar(35, close="100.35", high="100.39", low="100.25", volume=100),
        bar(40, close="100.65", high="100.70", low="100.34", volume=120),
    ]

    assert strategy.evaluate(bars, datetime(2026, 8, 3, 10, 16, tzinfo=ET)) is None
