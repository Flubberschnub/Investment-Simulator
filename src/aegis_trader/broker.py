from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from alpaca.common.enums import Sort
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    MarketOrderRequest,
    StopLossRequest,
    TakeProfitRequest,
)

from aegis_trader.config import Settings
from aegis_trader.models import (
    AccountSnapshot,
    Bar,
    MarketClock,
    OrderPlan,
    OrderSnapshot,
    PositionSnapshot,
    Quote,
    decimal_from,
)


class AlpacaPaperBroker:
    """Thin Alpaca adapter that is structurally locked to paper trading."""

    def __init__(self, settings: Settings) -> None:
        api_key, secret_key = settings.require_alpaca_credentials()
        self.settings = settings
        self.trading = TradingClient(api_key, secret_key, paper=True)
        self.market_data = StockHistoricalDataClient(api_key, secret_key)

    def get_clock(self) -> MarketClock:
        clock = self.trading.get_clock()
        return MarketClock(
            timestamp=clock.timestamp,
            is_open=bool(clock.is_open),
            next_open=clock.next_open,
            next_close=clock.next_close,
        )

    def get_account(self) -> AccountSnapshot:
        account = self.trading.get_account()
        return AccountSnapshot(
            equity=decimal_from(account.equity),
            last_equity=decimal_from(account.last_equity),
            buying_power=decimal_from(account.buying_power),
            trading_blocked=bool(account.trading_blocked),
        )

    def get_positions(self) -> list[PositionSnapshot]:
        positions = self.trading.get_all_positions()
        return [
            PositionSnapshot(
                symbol=str(position.symbol),
                quantity=decimal_from(position.qty),
                market_value=decimal_from(position.market_value),
            )
            for position in positions
        ]

    def get_open_orders(self, symbol: str | None = None) -> list[OrderSnapshot]:
        request = GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbols=[symbol] if symbol else None,
            nested=True,
        )
        orders = self.trading.get_orders(filter=request)
        return [self._to_order_snapshot(order) for order in orders]

    def order_exists(self, client_order_id: str, after: datetime) -> bool:
        orders = self._get_orders_after(after)
        return any(str(order.client_order_id) == client_order_id for order in orders)

    def get_bot_order_count(self, after: datetime) -> int:
        orders = self._get_orders_after(after)
        return len(
            {
                str(order.client_order_id)
                for order in orders
                if str(order.client_order_id).startswith("aegis-orb-")
            }
        )

    def _get_orders_after(self, after: datetime) -> list[Any]:
        request = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            after=after,
            direction=Sort.DESC,
            limit=100,
            nested=True,
        )
        return list(self.trading.get_orders(filter=request))

    def get_bars(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame(self.settings.bar_minutes, TimeFrameUnit.Minute),
            start=start,
            end=end,
            feed=DataFeed.IEX,
            sort=Sort.ASC,
        )
        response = self.market_data.get_stock_bars(request)
        api_bars = response.data.get(symbol, [])
        return [
            Bar(
                timestamp=bar.timestamp,
                open=decimal_from(bar.open),
                high=decimal_from(bar.high),
                low=decimal_from(bar.low),
                close=decimal_from(bar.close),
                volume=int(bar.volume),
            )
            for bar in api_bars
        ]

    def get_latest_quote(self, symbol: str) -> Quote:
        request = StockLatestQuoteRequest(symbol_or_symbols=symbol, feed=DataFeed.IEX)
        response = self.market_data.get_stock_latest_quote(request)
        quote = response[symbol]
        return Quote(
            timestamp=quote.timestamp,
            bid=decimal_from(quote.bid_price),
            ask=decimal_from(quote.ask_price),
        )

    def submit_bracket_order(self, plan: OrderPlan) -> OrderSnapshot:
        request = MarketOrderRequest(
            symbol=plan.symbol,
            qty=plan.quantity,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            client_order_id=plan.client_order_id,
            take_profit=TakeProfitRequest(limit_price=float(plan.target_price)),
            stop_loss=StopLossRequest(stop_price=float(plan.stop_price)),
        )
        order = self.trading.submit_order(order_data=request)
        return self._to_order_snapshot(order)

    def flatten_account(self) -> list[Any] | dict[str, Any]:
        return self.trading.close_all_positions(cancel_orders=True)

    def cancel_all_orders(self) -> list[Any] | dict[str, Any]:
        return self.trading.cancel_orders()

    @staticmethod
    def _to_order_snapshot(order: Any) -> OrderSnapshot:
        return OrderSnapshot(
            id=str(order.id),
            client_order_id=str(order.client_order_id),
            symbol=str(order.symbol or ""),
            status=str(getattr(order.status, "value", order.status)),
        )
