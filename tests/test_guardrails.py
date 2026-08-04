from decimal import Decimal

import pytest
from pydantic import ValidationError

from aegis_trader.config import Settings
from aegis_trader.service import make_client_order_id


def test_client_order_id_is_deterministic_and_short() -> None:
    first = make_client_order_id("TQQQ:2026-08-03T10:10:00-04:00:orb-v1")
    second = make_client_order_id("TQQQ:2026-08-03T10:10:00-04:00:orb-v1")
    assert first == second
    assert len(first) <= 48


def test_risk_configuration_has_hard_upper_bounds() -> None:
    with pytest.raises(ValidationError):
        Settings(risk_per_trade_pct=Decimal("0.05"))
