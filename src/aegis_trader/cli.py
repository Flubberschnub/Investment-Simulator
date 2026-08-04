from __future__ import annotations

import json
import logging
from typing import Annotated

import typer

from aegis_trader.config import Settings
from aegis_trader.service import TradingService
from aegis_trader.state import StateStore

app = typer.Typer(
    help="Aegis paper-only trading bot. This application cannot connect to Alpaca live trading.",
    no_args_is_help=True,
)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@app.command()
def run() -> None:
    """Run the continuous paper-trading worker."""

    settings = Settings()
    configure_logging(settings.log_level)
    settings.require_alpaca_credentials()
    TradingService(settings).run_forever()


@app.command()
def once() -> None:
    """Run one paper-trading evaluation cycle."""

    settings = Settings()
    configure_logging(settings.log_level)
    settings.require_alpaca_credentials()
    result = TradingService(settings).run_cycle()
    typer.echo(json.dumps({"status": result.status, "message": result.message, **result.details}))


@app.command()
def status(events: Annotated[int, typer.Option(min=0, max=100)] = 10) -> None:
    """Show local bot state and recent audit events."""

    settings = Settings()
    state = StateStore(settings.database_path)
    output = state.status_summary()
    output["symbol"] = settings.symbol
    output["recent_events"] = state.recent_events(events) if events else []
    typer.echo(json.dumps(output, indent=2, default=str))


@app.command()
def pause(reason: str = "Paused manually") -> None:
    """Prevent the worker from opening new positions."""

    settings = Settings()
    StateStore(settings.database_path).set_paused(True, reason)
    typer.echo("Trading paused. End-of-day flattening remains active.")


@app.command()
def resume(
    acknowledge_paper_only: Annotated[
        bool,
        typer.Option("--acknowledge-paper-only", help="Required safety acknowledgement."),
    ] = False,
) -> None:
    """Allow the worker to evaluate new paper trades again."""

    if not acknowledge_paper_only:
        raise typer.BadParameter("Pass --acknowledge-paper-only to resume")
    settings = Settings()
    StateStore(settings.database_path).set_paused(False, "Resumed manually")
    typer.echo("Paper trading resumed.")


@app.command()
def flatten(
    confirmation: Annotated[
        str,
        typer.Option("--confirm", help="Type PAPER to close paper positions and cancel orders."),
    ],
) -> None:
    """Close every paper position and cancel every paper order."""

    if confirmation != "PAPER":
        raise typer.BadParameter("Confirmation must be exactly PAPER")
    settings = Settings()
    settings.require_alpaca_credentials()
    from aegis_trader.broker import AlpacaPaperBroker

    broker = AlpacaPaperBroker(settings)
    broker.flatten_account()
    StateStore(settings.database_path).record_event(
        level="WARNING",
        kind="manual_flatten",
        message="Paper account flattened manually",
    )
    typer.echo("Paper positions closed and paper orders cancelled.")


@app.command()
def doctor() -> None:
    """Verify configuration and Alpaca paper-account connectivity."""

    settings = Settings()
    settings.require_alpaca_credentials()
    from aegis_trader.broker import AlpacaPaperBroker

    broker = AlpacaPaperBroker(settings)
    account = broker.get_account()
    clock = broker.get_clock()
    typer.echo(
        json.dumps(
            {
                "paper_only": True,
                "symbol": settings.symbol,
                "equity": str(account.equity),
                "buying_power": str(account.buying_power),
                "trading_blocked": account.trading_blocked,
                "market_open": clock.is_open,
                "broker_time": clock.timestamp.isoformat(),
                "database": str(settings.database_path),
            },
            indent=2,
        )
    )
