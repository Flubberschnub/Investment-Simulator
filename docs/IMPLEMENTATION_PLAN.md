# Implementation Plan

## Goal

Build a reproducible, observable paper-trading service that can evaluate one approved strategy automatically while keeping broker execution behind non-bypassable risk controls.

## Implemented milestones

### Milestone 0 — Safety foundation

- Paper-only Alpaca adapter: `TradingClient(..., paper=True)` is hard-coded.
- No live endpoint, live flag, arbitrary-symbol order tool, options, shorts, margin strategy, or averaging down.
- Whole-share sizing based on maximum loss per trade and maximum position notional.
- Daily-loss circuit breaker, maximum daily trades, one-position/one-order limit, stale-quote rejection, spread rejection, and mandatory end-of-day flattening.
- Deterministic client order IDs for retry idempotency.
- SQLite audit log and persistent pause state.

### Milestone 1 — Automated paper strategy

- Long-only TQQQ 15-minute opening-range breakout.
- Five-minute bars, VWAP confirmation, relative-volume confirmation, maximum extension filter, and maximum stop-distance filter.
- Broker-side bracket order with stop loss and take profit.
- Continuous worker and one-cycle CLI mode.

### Milestone 2 — Supervision and operations

- MCP tools for status, audit events, emergency pause, and acknowledged paper resume.
- Docker and Compose deployment.
- Unit tests and GitHub Actions CI.

## Next milestones before considering real money

1. Add a historical backtest module using the exact live strategy implementation.
2. Add a shadow mode that records expected orders against live data without submission.
3. Run at least 30 market sessions in paper mode and reconcile every expected order, fill, stop, target, restart, and disconnect.
4. Add order-update streaming and explicit reconciliation of partially filled bracket legs.
5. Add metrics/alerts for process health, quote age, broker connectivity, open risk, and daily drawdown.
6. Conduct a manual code and security review.
7. Keep live trading in a separate repository or separately reviewed release rather than adding an environment switch to this service.
