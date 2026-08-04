from __future__ import annotations

from typing import Any

import httpx

from aegis_trader.config import ExecutionMode, Settings


class LiveTradingDisabled(RuntimeError):
    pass


class SchwabClient:
    """Minimal Schwab read/shadow adapter.

    Order submission is intentionally disabled in v0.2. Market-data and account reads
    require a user-supplied OAuth access token from a Schwab developer application.
    """

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self._client = httpx.Client(timeout=20, transport=transport)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.require_schwab_token()}"}

    def get_quote(self, symbol: str) -> dict[str, Any]:
        response = self._client.get(
            f"{self.settings.schwab_market_base_url}/quotes",
            params={"symbols": symbol, "fields": "quote"},
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    def get_account_numbers(self) -> list[dict[str, Any]]:
        response = self._client.get(
            f"{self.settings.schwab_trader_base_url}/accounts/accountNumbers",
            headers=self.headers,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected Schwab account-number response")
        return payload

    def place_order(self, order: dict[str, Any]) -> None:
        del order
        mode = self.settings.execution_mode
        if mode is not ExecutionMode.SCHWAB_LIVE:
            raise LiveTradingDisabled("Order submission is unavailable outside schwab_live mode")
        raise LiveTradingDisabled(
            "Live Schwab submission is intentionally not implemented in v0.2. "
            "It requires written employee-compliance approval and a separately reviewed release."
        )
