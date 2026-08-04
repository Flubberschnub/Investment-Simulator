# Schwab setup

1. Confirm with Employee Compliance that personal automated-trading research, developer API access, leveraged ETFs, same-day round trips, and any eventual automated submission are permitted.
2. Create a Schwab developer application and configure its HTTPS callback URL.
3. Complete Schwab OAuth manually and store the access token outside Git.
4. Set `AEGIS_EXECUTION_MODE=schwab_shadow` and run `aegis-trader schwab-doctor`.
5. Compare shadow signals with the thinkorswim paperMoney strategy and local backtests.

## Current safety lock

`SchwabClient.place_order()` is intentionally nonfunctional. Setting `schwab_live`, compliance flags, or an account hash does not enable transmission in this release.

## Token handling

Use an OS secret store or a managed secret service for long-running deployments. The `.env` workflow is only a local-development convenience and `.env` is ignored by Git.
