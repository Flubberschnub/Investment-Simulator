from __future__ import annotations

from decimal import Decimal

from aegis_trader.config import Settings
from aegis_trader.models import Bar, Signal


class OpeningRangeBreakout:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, bars: list[Bar]) -> Signal | None:
        if len(bars) < max(4, self.settings.volume_lookback + 1):
            return None
        session_date = bars[-1].timestamp.date()
        session = [bar for bar in bars if bar.timestamp.date() == session_date]
        if len(session) < max(4, self.settings.volume_lookback + 1):
            return None

        opening = session[:3]
        current = session[-1]
        previous = session[-2]
        opening_high = max(bar.high for bar in opening)
        if not (previous.close <= opening_high < current.close):
            return None

        cumulative_pv = sum(
            ((bar.high + bar.low + bar.close) / Decimal("3")) * bar.volume for bar in session
        )
        cumulative_volume = sum(bar.volume for bar in session)
        vwap = cumulative_pv / Decimal(cumulative_volume)
        if current.close <= vwap:
            return None

        lookback = session[-(self.settings.volume_lookback + 1) : -1]
        average_volume = Decimal(sum(bar.volume for bar in lookback)) / Decimal(len(lookback))
        if Decimal(current.volume) < average_volume * self.settings.volume_factor:
            return None

        extension = (current.close - opening_high) / opening_high
        if extension > self.settings.max_extension_pct:
            return None

        stop = min(current.low, opening_high)
        stop_pct = (current.close - stop) / current.close
        if stop_pct <= 0 or stop_pct > self.settings.max_stop_pct:
            return None
        target = current.close + (current.close - stop) * self.settings.reward_to_risk
        return Signal(
            timestamp=current.timestamp,
            symbol=self.settings.symbol,
            entry=current.close,
            stop=stop,
            target=target,
            reason="opening-range breakout above VWAP with relative volume",
        )
