from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from aegis_trader.config import Settings
from aegis_trader.models import Bar, StrategySignal


REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
TICK_SIZE = Decimal("0.01")


class OpeningRangeBreakoutStrategy:
    """Long-only opening-range breakout with VWAP and volume confirmation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.market_tz = ZoneInfo(settings.market_timezone)

    def evaluate(self, bars: list[Bar], now: datetime) -> StrategySignal | None:
        if not bars:
            return None

        now_et = now.astimezone(self.market_tz)
        session_date = now_et.date()
        session_open = datetime.combine(session_date, REGULAR_OPEN, self.market_tz)
        opening_end = session_open + timedelta(minutes=self.settings.opening_range_minutes)
        entry_start = datetime.combine(session_date, self.settings.entry_start, self.market_tz)
        entry_cutoff = datetime.combine(session_date, self.settings.entry_cutoff, self.market_tz)

        completed: list[Bar] = []
        bar_duration = timedelta(minutes=self.settings.bar_minutes)
        for bar in sorted(bars, key=lambda item: item.timestamp):
            timestamp_et = bar.timestamp.astimezone(self.market_tz)
            if timestamp_et.date() != session_date:
                continue
            if not (REGULAR_OPEN <= timestamp_et.time() < REGULAR_CLOSE):
                continue
            if timestamp_et + bar_duration > now_et:
                continue
            completed.append(bar)

        opening_bars = [
            bar
            for bar in completed
            if session_open <= bar.timestamp.astimezone(self.market_tz) < opening_end
        ]
        expected_opening_bars = self.settings.opening_range_minutes // self.settings.bar_minutes
        if len(opening_bars) < expected_opening_bars:
            return None

        tradable_bars = [
            bar
            for bar in completed
            if entry_start <= bar.timestamp.astimezone(self.market_tz) <= entry_cutoff
        ]
        if len(tradable_bars) < 2:
            return None

        latest = tradable_bars[-1]
        previous = tradable_bars[-2]
        latest_et = latest.timestamp.astimezone(self.market_tz)
        if not (entry_start <= latest_et <= entry_cutoff):
            return None

        opening_range_high = max(bar.high for bar in opening_bars)
        if latest.close <= opening_range_high:
            return None
        if previous.close > opening_range_high:
            return None

        session_bars = [
            bar
            for bar in completed
            if session_open <= bar.timestamp.astimezone(self.market_tz) <= latest_et
        ]
        vwap = self._calculate_vwap(session_bars)
        if vwap is None or latest.close <= vwap:
            return None

        earlier = [bar for bar in session_bars if bar.timestamp < latest.timestamp]
        volume_window = earlier[-self.settings.volume_lookback :]
        if len(volume_window) < self.settings.volume_lookback:
            return None
        average_volume = Decimal(sum(bar.volume for bar in volume_window)) / Decimal(
            len(volume_window)
        )
        if Decimal(latest.volume) < average_volume * self.settings.volume_factor:
            return None

        extension = (latest.close - opening_range_high) / opening_range_high
        if extension > self.settings.max_extension_pct:
            return None

        stop_price = min(latest.low, opening_range_high - TICK_SIZE)
        if stop_price <= 0 or stop_price >= latest.close:
            return None
        per_share_risk = latest.close - stop_price
        if per_share_risk / latest.close > self.settings.max_stop_pct:
            return None

        target_price = latest.close + (per_share_risk * self.settings.reward_to_risk)
        signal_key = f"{self.settings.symbol}:{latest.timestamp.isoformat()}:orb-v1"
        return StrategySignal(
            symbol=self.settings.symbol,
            timestamp=latest.timestamp,
            signal_key=signal_key,
            entry_estimate=latest.close.quantize(TICK_SIZE),
            stop_price=stop_price.quantize(TICK_SIZE),
            target_price=target_price.quantize(TICK_SIZE),
            opening_range_high=opening_range_high.quantize(TICK_SIZE),
            vwap=vwap.quantize(TICK_SIZE),
            reason="5-minute opening-range breakout above VWAP with volume confirmation",
        )

    @staticmethod
    def _calculate_vwap(bars: list[Bar]) -> Decimal | None:
        total_volume = sum(bar.volume for bar in bars)
        if total_volume <= 0:
            return None
        weighted = sum(
            (((bar.high + bar.low + bar.close) / Decimal("3")) * Decimal(bar.volume))
            for bar in bars
        )
        return weighted / Decimal(total_volume)
