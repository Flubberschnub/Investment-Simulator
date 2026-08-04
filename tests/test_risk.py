from decimal import Decimal

from aegis_trader.config import Settings
from aegis_trader.models import AccountSnapshot
from aegis_trader.risk import RiskManager


def account(equity: str = "1000", last_equity: str = "1000") -> AccountSnapshot:
    return AccountSnapshot(
        equity=Decimal(equity),
        last_equity=Decimal(last_equity),
        buying_power=Decimal(equity),
        trading_blocked=False,
    )


def test_position_size_is_capped_by_notional() -> None:
    manager = RiskManager(Settings())
    decision = manager.evaluate(
        account=account(),
        entry_price=Decimal("80"),
        stop_price=Decimal("79.50"),
        daily_trades=0,
        open_positions=0,
        open_orders=0,
    )

    assert decision.allowed
    assert decision.quantity == 3
    assert decision.estimated_notional == Decimal("240")


def test_daily_loss_triggers_halt() -> None:
    manager = RiskManager(Settings(max_daily_loss_pct=Decimal("0.01")))
    decision = manager.evaluate(
        account=account(equity="989", last_equity="1000"),
        entry_price=Decimal("80"),
        stop_price=Decimal("79.50"),
        daily_trades=0,
        open_positions=0,
        open_orders=0,
    )

    assert not decision.allowed
    assert decision.halt_trading
