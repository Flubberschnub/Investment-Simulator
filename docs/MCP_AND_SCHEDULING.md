# MCP and Scheduling

## Responsibility split

The worker owns market timing and order execution. It polls Alpaca while the market is open and evaluates completed five-minute bars. ChatGPT scheduled tasks should not be the execution clock because they are not designed for low-latency or exactly-once intraday order submission.

MCP is intentionally supervisory:

- `get_bot_status`
- `get_recent_events`
- `pause_trading`
- `resume_paper_trading` with the exact acknowledgement `PAPER ONLY`

There is no MCP tool for arbitrary orders or strategy/risk mutation.

## Local MCP over stdio

```bash
AEGIS_MCP_TRANSPORT=stdio aegis-mcp
```

## Streamable HTTP

```bash
AEGIS_MCP_TRANSPORT=streamable-http \
AEGIS_MCP_HOST=127.0.0.1 \
AEGIS_MCP_PORT=8765 \
aegis-mcp
```

Or:

```bash
docker compose --profile mcp up -d --build
```

The Compose port binds to localhost only. Put authentication and TLS in front of it before exposing it beyond the machine.

## Useful scheduled tasks after deployment

A scheduled assistant can call MCP to send a premarket health check, an end-of-day trade summary, or an alert when the bot is paused. The autonomous worker should remain responsible for actual entries and exits.
