from datetime import datetime, timedelta
from decimal import Decimal

from aegis_trader.config import Settings
from aegis_trader.models import Bar
from aegis_trader.strategy import OpeningRangeBreakout


def test_breakout_signal() -> None:
    start = datetime.fromisoformat("2026-08-03T09:30:00-04:00")
    closes = ["100", "100.1", "100.2", "100.1", "100.15", "100.25", "100.55"]
    volumes = [100, 100, 100, 100, 100, 100, 200]
    bars = [
        Bar(
            start + timedelta(minutes=5 * i),
            Decimal(close),
            Decimal(close) + Decimal("0.05"),
            Decimal(close) - Decimal("0.05"),
            Decimal(close),
            volumes[i],
        )
        for i, close in enumerate(closes)
    ]
    signal = OpeningRangeBreakout(Settings(volume_factor=Decimal("1.1"))).evaluate(bars)
    assert signal is not None
    assert signal.stop < signal.entry < signal.target
