from decimal import ROUND_DOWN, Decimal

from aegis_trader.config import Settings
from aegis_trader.models import RiskDecision


class RiskGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def size_trade(
        self,
        equity: Decimal,
        entry: Decimal,
        stop: Decimal,
        day_pnl: Decimal = Decimal("0"),
        trades_today: int = 0,
    ) -> RiskDecision:
        if day_pnl <= -(equity * self.settings.max_daily_loss_pct):
            return RiskDecision(False, reason="daily loss limit reached")
        if trades_today >= self.settings.max_trades_per_day:
            return RiskDecision(False, reason="daily trade limit reached")
        per_share_risk = entry - stop
        if per_share_risk <= 0:
            return RiskDecision(False, reason="stop must be below entry")

        risk_budget = equity * self.settings.risk_per_trade_pct
        risk_qty = int((risk_budget / per_share_risk).to_integral_value(rounding=ROUND_DOWN))
        notional_budget = equity * self.settings.max_position_notional_pct
        notional_qty = int((notional_budget / entry).to_integral_value(rounding=ROUND_DOWN))
        quantity = min(risk_qty, notional_qty)
        if quantity < 1:
            return RiskDecision(False, reason="account too small for configured risk")
        return RiskDecision(True, quantity=quantity, reason="approved")
