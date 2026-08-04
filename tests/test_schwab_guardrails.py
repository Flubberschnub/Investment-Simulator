import httpx
import pytest
from pydantic import ValidationError

from aegis_trader.config import ExecutionMode, Settings
from aegis_trader.schwab import LiveTradingDisabled, SchwabClient


def test_live_mode_requires_compliance_ack() -> None:
    with pytest.raises(ValidationError):
        Settings(execution_mode=ExecutionMode.SCHWAB_LIVE)


def test_order_submission_remains_disabled_even_with_ack() -> None:
    settings = Settings(
        execution_mode=ExecutionMode.SCHWAB_LIVE,
        compliance_approved=True,
        live_trading_ack="I_HAVE_WRITTEN_COMPLIANCE_APPROVAL",
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    client = SchwabClient(settings, transport=transport)
    with pytest.raises(LiveTradingDisabled):
        client.place_order({"symbol": "TQQQ"})
