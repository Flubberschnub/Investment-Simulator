from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from aegis_trader.config import Settings
from aegis_trader.models import AccountSnapshot, RiskDecision


class RiskManager:
    """Hard risk gateway. Strategy code cannot override these checks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(
        self,
        *,
        account: AccountSnapshot,
        entry_price: Decimal,
        stop_price: Decimal,
        daily_trades: int,
        open_positions: int,
        open_orders: int,
    ) -> RiskDecision:
        if account.trading_blocked:
            return RiskDecision(False, "Broker reports trading is blocked", halt_trading=True)
        if account.equity <= 0 or account.last_equity <= 0:
            return RiskDecision(False, "Account equity is not positive", halt_trading=True)

        daily_loss_limit = account.last_equity * self.settings.max_daily_loss_pct
        if account.daily_pnl <= -daily_loss_limit:
            return RiskDecision(
                False,
                "Daily loss circuit breaker reached",
                halt_trading=True,
            )
        if open_positions > 0:
            return RiskDecision(False, "An open position already exists")
        if open_orders > 0:
            return RiskDecision(False, "An open order already exists")
        if daily_trades >= self.settings.max_trades_per_day:
            return RiskDecision(False, "Maximum trades for the day reached")
        if entry_price <= 0 or stop_price <= 0 or stop_price >= entry_price:
            return RiskDecision(False, "Invalid entry or stop price")

        per_share_risk = entry_price - stop_price
        if per_share_risk / entry_price > self.settings.max_stop_pct:
            return RiskDecision(False, "Stop distance exceeds maximum")

        risk_budget = account.equity * self.settings.risk_per_trade_pct
        max_notional = min(
            account.equity * self.settings.max_position_notional_pct,
            account.buying_power,
        )
        quantity_by_risk = int(
            (risk_budget / per_share_risk).to_integral_value(rounding=ROUND_DOWN)
        )
        quantity_by_notional = int(
            (max_notional / entry_price).to_integral_value(rounding=ROUND_DOWN)
        )
        quantity = min(quantity_by_risk, quantity_by_notional)
        if quantity < 1:
            return RiskDecision(
                False,
                "Account is too small for one whole share within configured risk limits",
                risk_budget=risk_budget,
            )

        estimated_notional = entry_price * Decimal(quantity)
        return RiskDecision(
            True,
            "Risk checks passed",
            quantity=quantity,
            risk_budget=risk_budget,
            estimated_notional=estimated_notional,
        )
