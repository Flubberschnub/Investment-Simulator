from datetime import date
from pathlib import Path

from aegis_trader.state import StateStore


def test_pause_and_order_audit(tmp_path: Path) -> None:
    state = StateStore(tmp_path / "state.db")
    assert state.get_pause_state() == (False, "")

    state.set_paused(True, "test halt")
    assert state.get_pause_state() == (True, "test halt")

    state.record_order(
        client_order_id="abc",
        trade_date=date(2026, 8, 3),
        signal_key="signal",
        broker_order_id="broker-1",
        status="accepted",
        payload={"quantity": 1},
    )
    assert state.has_order("abc")
    assert state.count_orders_for_day(date(2026, 8, 3)) == 1
    assert state.recent_events(1)[0]["kind"] == "pause_state"
