from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from aegis_trader.config import Settings
from aegis_trader.state import StateStore

settings = Settings()
mcp = FastMCP(
    "Aegis Paper Trader",
    instructions=(
        "Supervisory tools for a paper-only trading bot. There is no arbitrary order tool and "
        "no live-trading mode. Use pause_trading as the emergency control."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
)


def _state() -> StateStore:
    return StateStore(settings.database_path)


@mcp.tool()
def get_bot_status() -> dict[str, Any]:
    """Return paper-only status, pause state, symbol, and local audit counts."""

    result = _state().status_summary()
    result["symbol"] = settings.symbol
    result["strategy"] = "long-only 15-minute opening-range breakout v1"
    return result


@mcp.tool()
def get_recent_events(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent paper-trading audit events, newest first."""

    return _state().recent_events(limit)


@mcp.tool()
def pause_trading(reason: str = "Paused through MCP") -> dict[str, Any]:
    """Emergency stop: prevent new entries. End-of-day flattening remains active."""

    state = _state()
    state.set_paused(True, reason)
    return state.status_summary()


@mcp.tool()
def resume_paper_trading(acknowledgement: str) -> dict[str, Any]:
    """Resume entries only when acknowledgement is exactly PAPER ONLY."""

    if acknowledgement != "PAPER ONLY":
        return {
            "resumed": False,
            "error": "Acknowledgement must be exactly PAPER ONLY",
        }
    state = _state()
    state.set_paused(False, "Resumed through MCP with paper-only acknowledgement")
    return {"resumed": True, **state.status_summary()}


def main() -> None:
    transport = os.getenv("AEGIS_MCP_TRANSPORT", settings.mcp_transport).strip().lower()
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    elif transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
