# Implementation plan

## Completed in v0.2

- Remove the Alpaca dependency and credentials.
- Add deterministic historical simulation.
- Add conservative fill assumptions and risk controls.
- Add Schwab OAuth-token-based read/shadow adapter.
- Add a hard non-bypassable live-order exception.
- Add thinkScript strategy parity artifact.
- Restrict MCP to supervisory controls.

## Required before a live-capable release

1. Written Employee Compliance approval covering automation and intended instruments.
2. Private repository and external secret storage.
3. Official Schwab specification review for every endpoint and order schema.
4. Token lifecycle, reauthorization, rate-limit, timeout, and stale-data handling.
5. Full order-state reconciliation, idempotency, partial-fill handling, and restart recovery.
6. At least 30 market sessions of reconciled shadow operation.
7. Independent code review and approval-gated first live orders.
8. A separate release in which live submission is added; never patch around the v0.2 exception.
