# Aegis Paper Trader

A safety-first, **paper-only** intraday trading bot built with Python, Alpaca, and an optional MCP supervisory server.

> This repository is experimental software, not investment advice. Paper fills do not reproduce all live-market effects, including slippage, partial fills, queue position, liquidity, halts, and outages.

## Safety boundary

This release cannot select Alpaca live trading. The broker adapter constructs `TradingClient(..., paper=True)` directly and exposes no setting that can change it. It also excludes options, shorts, overnight positions, averaging down, and arbitrary MCP order placement.

Hard controls include:

- 0.25% account-equity risk budget per planned trade by default
- 1% account daily-loss circuit breaker by default
- 25% maximum position notional by default
- One position and one open order at a time
- Three submitted trades per day maximum
- Broker-side stop and take-profit bracket
- Stale quote and wide spread rejection
- Forced flatten beginning at 3:50 p.m. Eastern
- Deterministic client order IDs to prevent duplicate retries
- Persistent emergency pause and SQLite audit trail

## Strategy v1

The approved strategy is a long-only TQQQ opening-range breakout:

1. Build the opening range from 9:30–9:45 a.m. Eastern.
2. Evaluate completed five-minute bars between 9:45 a.m. and 2:00 p.m.
3. Require a fresh close above the opening-range high.
4. Require price above session VWAP.
5. Require elevated volume relative to the previous five bars.
6. Reject extended entries, large stops, stale quotes, and wide spreads.
7. Submit a whole-share market bracket order sized by the risk gateway.

The strategy is intentionally simple and deterministic so every decision can be reproduced.

## Setup

Requirements: Python 3.11+ and a dedicated Alpaca paper-trading account. The bot performs account-wide safety checks and end-of-day flattening, so do not share that paper account with unrelated experiments.

```bash
git clone https://github.com/Flubberschnub/Investment-Simulator.git
cd Investment-Simulator
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
cp .env.example .env
```

Add **paper** API credentials to `.env`:

```dotenv
AEGIS_ALPACA_API_KEY=your-paper-key
AEGIS_ALPACA_SECRET_KEY=your-paper-secret
```

Verify the connection:

```bash
aegis-trader doctor
```

Run one evaluation without starting a daemon:

```bash
aegis-trader once
```

Run continuously:

```bash
aegis-trader run
```

## Emergency controls

```bash
aegis-trader pause "manual review"
aegis-trader status
aegis-trader flatten --confirm PAPER
aegis-trader resume --acknowledge-paper-only
```

Pausing blocks new entries but does not disable the end-of-day flatten path.

## Docker

```bash
cp .env.example .env
# Fill in paper credentials
docker compose up -d --build trader
docker compose logs -f trader
```

To also run MCP locally:

```bash
docker compose --profile mcp up -d --build
```

See [`docs/MCP_AND_SCHEDULING.md`](docs/MCP_AND_SCHEDULING.md).

## Tests

```bash
ruff check .
pytest --cov=aegis_trader
```

## Before any real-money implementation

Do not turn this into a live bot merely by replacing `paper=True`. Complete the verification roadmap in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md), especially backtesting, shadow trading, order-stream reconciliation, multi-week paper operation, and an independent code review.
