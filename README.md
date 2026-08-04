# Aegis Schwab Trader

A safety-first trading research project for a Schwab-only account environment.

## What v0.2 can do

- Backtest the TQQQ opening-range breakout against local OHLCV CSV files.
- Apply deterministic position sizing and daily-loss/trade-count controls.
- Connect to the Schwab Trader API for authorized account discovery.
- Connect to Schwab market data for read/shadow workflows.
- Run an MCP supervisor that can inspect, pause, and resume simulation/shadow mode.
- Import a matching thinkScript strategy into thinkorswim for hypothetical testing.

## What v0.2 cannot do

**It cannot submit a live order.** `SchwabClient.place_order()` always raises. Live execution requires written employee-compliance approval and a separately reviewed release. thinkScript strategy signals are hypothetical and do not transmit orders.

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
cp .env.example .env
```

## Local backtest

CSV columns: `timestamp,open,high,low,close,volume` with ISO-8601 timestamps.

```bash
aegis-trader backtest data/TQQQ_5m.csv
```

The simulator uses a conservative same-bar rule: if a stop and target are both touched, the stop is assumed to fill first.

## thinkorswim

Import `thinkscript/Aegis_ORB_Strategy.ts` as a Strategy on a five-minute chart. Use it in paperMoney to compare chart signals with Python backtests. It is not an automated-order bridge.

## Schwab shadow setup

See `docs/SCHWAB_SETUP.md`. Keep the repository private before adding any account-specific configuration, and never commit OAuth tokens.

```bash
AEGIS_EXECUTION_MODE=schwab_shadow aegis-trader schwab-doctor
```

## MCP safety surface

The MCP server exposes status, pause, and simulation/shadow resume only. It exposes no order-placement tool and refuses live-mode resume.

```bash
aegis-mcp
```
