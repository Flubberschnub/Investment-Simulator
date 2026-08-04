from decimal import Decimal

from aegis_trader.config import Settings
from aegis_trader.risk import RiskGateway


def test_position_size_respects_risk_and_notional() -> None:
    decision = RiskGateway(Settings()).size_trade(Decimal("10000"), Decimal("50"), Decimal("49"))
    assert decision.allowed
    assert decision.quantity == 25


def test_daily_loss_halts() -> None:
    decision = RiskGateway(Settings()).size_trade(
        Decimal("10000"), Decimal("50"), Decimal("49"), day_pnl=Decimal("-100")
    )
    assert not decision.allowed
