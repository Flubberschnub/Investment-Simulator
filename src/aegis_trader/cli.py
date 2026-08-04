from __future__ import annotations

import json
from pathlib import Path

import typer

from aegis_trader.config import ExecutionMode, Settings
from aegis_trader.schwab import SchwabClient
from aegis_trader.simulator import HistoricalSimulator, load_bars
from aegis_trader.state import StateStore

app = typer.Typer(no_args_is_help=True)


@app.command()
def status() -> None:
    settings = Settings()
    state = StateStore(settings.database_path)
    typer.echo(json.dumps({"mode": settings.execution_mode, **state.status()}, indent=2))


@app.command()
def backtest(csv_path: Path) -> None:
    settings = Settings(execution_mode=ExecutionMode.SIMULATION)
    report = HistoricalSimulator(settings).run(load_bars(csv_path))
    typer.echo(json.dumps(report.as_dict(), indent=2))


@app.command("schwab-doctor")
def schwab_doctor() -> None:
    settings = Settings()
    client = SchwabClient(settings)
    accounts = client.get_account_numbers()
    typer.echo(json.dumps({"connected": True, "authorized_accounts": len(accounts)}, indent=2))


@app.command()
def pause(reason: str = "manual review") -> None:
    settings = Settings()
    StateStore(settings.database_path).pause(reason)
    typer.echo("paused")


@app.command()
def resume(
    acknowledge_shadow_only: bool = typer.Option(False, "--acknowledge-shadow-only"),
) -> None:
    settings = Settings()
    if settings.execution_mode is not ExecutionMode.SIMULATION and not acknowledge_shadow_only:
        raise typer.BadParameter("Use --acknowledge-shadow-only for Schwab modes")
    StateStore(settings.database_path).resume()
    typer.echo("resumed")


@app.command("show-thinkscript")
def show_thinkscript() -> None:
    typer.echo("thinkscript/Aegis_ORB_Strategy.ts")


if __name__ == "__main__":
    app()
