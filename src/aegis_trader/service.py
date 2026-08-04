from __future__ import annotations

import hashlib
import logging
import time as time_module
from dataclasses import asdict
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from aegis_trader.config import Settings
from aegis_trader.models import CycleResult, OrderPlan
from aegis_trader.risk import RiskManager
from aegis_trader.state import StateStore
from aegis_trader.strategy import OpeningRangeBreakoutStrategy, REGULAR_OPEN, TICK_SIZE

LOGGER = logging.getLogger(__name__)


class BrokerProtocol(Protocol):
    def get_clock(self): ...  # type: ignore[no-untyped-def]
    def get_account(self): ...  # type: ignore[no-untyped-def]
    def get_positions(self): ...  # type: ignore[no-untyped-def]
    def get_open_orders(self, symbol: str | None = None): ...  # type: ignore[no-untyped-def]
    def order_exists(self, client_order_id: str, after: datetime) -> bool: ...
    def get_bot_order_count(self, after: datetime) -> int: ...
    def get_bars(
        self, symbol: str, start: datetime, end: datetime
    ): ...  # type: ignore[no-untyped-def]
    def get_latest_quote(self, symbol: str): ...  # type: ignore[no-untyped-def]
    def submit_bracket_order(self, plan: OrderPlan): ...  # type: ignore[no-untyped-def]
    def flatten_account(self): ...  # type: ignore[no-untyped-def]


class TradingService:
    def __init__(
        self,
        settings: Settings,
        *,
        broker: BrokerProtocol | None = None,
        state: StateStore | None = None,
    ) -> None:
        self.settings = settings
        if broker is None:
            from aegis_trader.broker import AlpacaPaperBroker

            broker = AlpacaPaperBroker(settings)
        self.broker = broker
        self.state = state or StateStore(settings.database_path)
        self.strategy = OpeningRangeBreakoutStrategy(settings)
        self.risk = RiskManager(settings)
        self.market_tz = ZoneInfo(settings.market_timezone)

    def run_forever(self) -> None:
        self.state.record_event(
            level="INFO",
            kind="service_started",
            message="Aegis paper-trading worker started",
            payload={"symbol": self.settings.symbol, "paper_only": True},
        )
        while True:
            try:
                result = self.run_cycle()
                LOGGER.info("cycle=%s message=%s", result.status, result.message)
            except Exception as exc:  # noqa: BLE001 - long-running worker boundary
                LOGGER.exception("Trading cycle failed")
                self.state.record_event(
                    level="ERROR",
                    kind="cycle_error",
                    message=str(exc),
                    payload={"exception_type": type(exc).__name__},
                )
            time_module.sleep(self.settings.poll_seconds)

    def run_cycle(self) -> CycleResult:
        clock = self.broker.get_clock()
        now_et = clock.timestamp.astimezone(self.market_tz)
        trade_date = now_et.date()

        if not clock.is_open:
            return CycleResult(
                "market_closed",
                "Market is closed",
                {"next_open": clock.next_open.isoformat()},
            )

        positions = self.broker.get_positions()
        open_orders = self.broker.get_open_orders()

        if now_et.time() >= self.settings.flatten_time:
            if positions or open_orders:
                self.broker.flatten_account()
                self.state.record_event(
                    level="WARNING",
                    kind="forced_flatten",
                    message="Closed positions and cancelled orders before market close",
                    payload={"time": now_et.isoformat()},
                )
            return CycleResult("flatten_window", "No new trades; end-of-day flatten window")

        paused, reason = self.state.get_pause_state()
        if paused:
            return CycleResult("paused", reason or "Trading is paused")

        account = self.broker.get_account()
        broker_lookup_start = datetime.combine(trade_date, time(0, 0), self.market_tz)
        daily_trades = max(
            self.state.count_orders_for_day(trade_date),
            self.broker.get_bot_order_count(broker_lookup_start),
        )
        preliminary = self.risk.evaluate(
            account=account,
            entry_price=Decimal("1"),
            stop_price=Decimal("0.99"),
            daily_trades=daily_trades,
            open_positions=len(positions),
            open_orders=len(open_orders),
        )
        if preliminary.halt_trading:
            self.broker.flatten_account()
            self.state.set_paused(True, preliminary.reason)
            return CycleResult("halted", preliminary.reason)
        if positions:
            return CycleResult("position_open", "Waiting for the existing position to close")
        if open_orders:
            return CycleResult("order_open", "Waiting for the existing order to resolve")
        if daily_trades >= self.settings.max_trades_per_day:
            return CycleResult("trade_limit", "Maximum trades for the day reached")
        if not (self.settings.entry_start <= now_et.time() <= self.settings.entry_cutoff):
            return CycleResult("outside_entry_window", "Outside configured entry window")

        session_open = datetime.combine(trade_date, REGULAR_OPEN, self.market_tz)
        bars = self.broker.get_bars(self.settings.symbol, session_open, clock.timestamp)
        signal = self.strategy.evaluate(bars, clock.timestamp)
        if signal is None:
            return CycleResult("no_signal", "Strategy conditions are not satisfied")

        quote = self.broker.get_latest_quote(self.settings.symbol)
        quote_age = (
            clock.timestamp.astimezone(UTC) - quote.timestamp.astimezone(UTC)
        ).total_seconds()
        if quote_age < 0 or quote_age > self.settings.quote_max_age_seconds:
            return CycleResult("stale_quote", "Latest quote is stale", {"age_seconds": quote_age})
        if quote.bid <= 0 or quote.ask <= 0 or quote.ask < quote.bid:
            return CycleResult("invalid_quote", "Latest quote is invalid")
        if quote.spread_bps > self.settings.max_spread_bps:
            return CycleResult(
                "spread_too_wide",
                "Bid-ask spread exceeds limit",
                {"spread_bps": str(quote.spread_bps)},
            )

        entry_price = quote.ask.quantize(TICK_SIZE)
        stop_price = signal.stop_price
        if stop_price >= entry_price:
            return CycleResult("invalid_stop", "Signal stop is not below the current ask")
        target_price = (
            entry_price + ((entry_price - stop_price) * self.settings.reward_to_risk)
        ).quantize(TICK_SIZE)

        decision = self.risk.evaluate(
            account=account,
            entry_price=entry_price,
            stop_price=stop_price,
            daily_trades=daily_trades,
            open_positions=0,
            open_orders=0,
        )
        if not decision.allowed:
            if decision.halt_trading:
                self.state.set_paused(True, decision.reason)
            return CycleResult("risk_rejected", decision.reason)

        client_order_id = make_client_order_id(signal.signal_key)
        if self.state.has_order(client_order_id) or self.broker.order_exists(
            client_order_id, broker_lookup_start
        ):
            return CycleResult("duplicate_prevented", "This signal was already submitted")

        plan = OrderPlan(
            symbol=self.settings.symbol,
            quantity=decision.quantity,
            entry_estimate=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            client_order_id=client_order_id,
            signal_key=signal.signal_key,
        )

        try:
            order = self.broker.submit_bracket_order(plan)
        except Exception as exc:
            # The signal is recorded even on failure. The bot will not retry the same
            # signal automatically; this avoids duplicate exposure after ambiguous errors.
            self.state.record_order(
                client_order_id=client_order_id,
                trade_date=trade_date,
                signal_key=signal.signal_key,
                broker_order_id=None,
                status="failed",
                payload={"error": str(exc), "plan": asdict(plan)},
            )
            self.state.record_event(
                level="ERROR",
                kind="order_submission_error",
                message=str(exc),
                payload={"client_order_id": client_order_id},
            )
            raise

        self.state.record_order(
            client_order_id=client_order_id,
            trade_date=trade_date,
            signal_key=signal.signal_key,
            broker_order_id=order.id,
            status=order.status,
            payload={
                "symbol": plan.symbol,
                "quantity": plan.quantity,
                "entry_estimate": str(plan.entry_estimate),
                "stop_price": str(plan.stop_price),
                "target_price": str(plan.target_price),
                "risk_budget": str(decision.risk_budget),
                "estimated_notional": str(decision.estimated_notional),
            },
        )
        self.state.record_event(
            level="INFO",
            kind="paper_order_submitted",
            message="Submitted paper bracket order",
            payload={
                "client_order_id": client_order_id,
                "broker_order_id": order.id,
                "symbol": plan.symbol,
                "quantity": plan.quantity,
                "entry_estimate": str(plan.entry_estimate),
                "stop_price": str(plan.stop_price),
                "target_price": str(plan.target_price),
            },
        )
        return CycleResult(
            "order_submitted",
            "Paper bracket order submitted",
            {"client_order_id": client_order_id, "broker_order_id": order.id},
        )


def make_client_order_id(signal_key: str) -> str:
    digest = hashlib.sha256(signal_key.encode("utf-8")).hexdigest()[:24]
    return f"aegis-orb-{digest}"
