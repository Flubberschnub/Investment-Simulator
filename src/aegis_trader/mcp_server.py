from __future__ import annotations

from aegis_trader.config import Settings
from aegis_trader.state import StateStore


def main() -> None:
    from mcp.server.fastmcp import FastMCP

    settings = Settings()
    state = StateStore(settings.database_path)
    server = FastMCP("aegis-schwab-supervisor")

    @server.tool()
    def get_bot_status() -> dict[str, object]:
        return {"execution_mode": settings.execution_mode.value, **state.status()}

    @server.tool()
    def pause_trading(reason: str) -> dict[str, object]:
        state.pause(reason)
        return state.status()

    @server.tool()
    def resume_shadow_or_simulation() -> dict[str, object]:
        if settings.execution_mode.value == "schwab_live":
            raise RuntimeError("MCP cannot resume live trading")
        state.resume()
        return state.status()

    server.run()
