"""
Abstract base class for live exchange integration tests.
Mirrors packages/additional_tests/exchanges_tests/abstract_authenticated_exchange_tester.py
but delegates to the Rust ExchangeTestRunner via octobot_connectors_rs.
"""
import asyncio
from abc import ABC, abstractmethod

from octobot_connectors import CcxtConnector, ExchangeConfig, ExchangeCredentials


class AbstractExchangeTester(ABC):
    # Override in subclasses
    EXCHANGE_NAME: str = ""
    EXCHANGE_TYPE: str = "spot"
    SYMBOL: str = "BTC/USDT"
    TIME_FRAME: str = "1h"
    ORDER_CURRENCY: str = "BTC"
    SETTLEMENT_CURRENCY: str = "USDT"
    ORDER_SIZE: int = 5          # % of portfolio
    ORDER_PRICE_DIFF: int = 10   # % from market price
    ALLOW_ZERO_MAKER_FEE: bool = False
    EXPECT_MISSING_ORDER_FEES: bool = False
    EXPECT_POSSIBLE_ORDER_NOT_FOUND: bool = False
    MARKET_FILL_TIMEOUT: int = 40
    OPEN_TIMEOUT: int = 30
    CANCEL_TIMEOUT: int = 30

    def __init__(self):
        self._config = None
        self._connector = None

    def get_config(self) -> ExchangeConfig:
        if self._config is None:
            self._config = self._build_config()
        return self._config

    def get_connector(self) -> CcxtConnector:
        if self._connector is None:
            self._connector = CcxtConnector(config=self.get_config())
        return self._connector

    def _build_config(self) -> ExchangeConfig:
        creds = self._load_credentials()
        return ExchangeConfig(
            exchange_name=self.EXCHANGE_NAME,
            is_future=self.EXCHANGE_TYPE == "future",
            credentials=creds,
        )

    def _load_credentials(self) -> ExchangeCredentials:
        import os
        key = os.environ.get(f"{self.EXCHANGE_NAME.upper()}_API_KEY", "")
        secret = os.environ.get(f"{self.EXCHANGE_NAME.upper()}_API_SECRET", "")
        password = os.environ.get(f"{self.EXCHANGE_NAME.upper()}_API_PASSWORD")
        return ExchangeCredentials(api_key=key, api_secret=secret, api_password=password)

    # ---- Test entrypoints (async) ----

    async def test_get_portfolio(self):
        connector = self.get_connector()
        await connector.initialize()
        balance = await connector.get_balance({})
        assert balance is not None
        await connector.stop()

    async def test_get_symbol_prices(self):
        connector = self.get_connector()
        await connector.initialize()
        from octobot_connectors import TimeFrame
        tf = getattr(TimeFrame, self._time_frame_variant(), TimeFrame.OneHour)
        candles = await connector.get_symbol_prices(self.SYMBOL, tf, 50, None, {})
        assert len(candles) > 0
        await connector.stop()

    async def test_get_order_book(self):
        connector = self.get_connector()
        await connector.initialize()
        ob = await connector.get_order_book(self.SYMBOL, 10)
        assert ob is not None
        assert len(ob.bids) > 0
        assert len(ob.asks) > 0
        await connector.stop()

    async def test_get_recent_trades(self):
        connector = self.get_connector()
        await connector.initialize()
        trades = await connector.get_recent_trades(self.SYMBOL, 10)
        assert isinstance(trades, list)
        await connector.stop()

    async def test_get_open_orders(self):
        connector = self.get_connector()
        await connector.initialize()
        orders = await connector.get_open_orders(self.SYMBOL, None, None)
        assert isinstance(orders, list)
        await connector.stop()

    async def test_get_closed_orders(self):
        connector = self.get_connector()
        await connector.initialize()
        orders = await connector.get_closed_orders(self.SYMBOL, None, 10)
        assert isinstance(orders, list)
        await connector.stop()

    async def test_get_my_recent_trades(self):
        connector = self.get_connector()
        await connector.initialize()
        trades = await connector.get_my_recent_trades(self.SYMBOL, None, 10)
        assert isinstance(trades, list)
        await connector.stop()

    async def test_create_and_cancel_limit_order(self):
        connector = self.get_connector()
        await connector.initialize()
        from octobot_connectors import TraderOrderType, TradeOrderSide
        import decimal

        # place far-from-market limit buy so it won't fill
        ticker = await connector.get_price_ticker(self.SYMBOL)
        current_price = ticker.last or ticker.close or ticker.bid
        order_price = current_price * (1 - self.ORDER_PRICE_DIFF / 100)

        order = await connector.create_order(
            TraderOrderType.BuyLimit,
            self.SYMBOL,
            decimal.Decimal("0.001"),
            decimal.Decimal(str(round(order_price, 8))),
            None,
            TradeOrderSide.Buy,
            decimal.Decimal(str(current_price)),
            False,
            None,
        )
        assert order is not None

        status = await connector.cancel_order(order.id, self.SYMBOL, TraderOrderType.BuyLimit)
        from octobot_connectors import OrderStatus
        assert status in (OrderStatus.Canceled, OrderStatus.Closed)
        await connector.stop()

    def _time_frame_variant(self) -> str:
        mapping = {
            "1m": "OneMinute", "3m": "ThreeMinutes", "5m": "FiveMinutes",
            "15m": "FifteenMinutes", "30m": "ThirtyMinutes",
            "1h": "OneHour", "2h": "TwoHours", "4h": "FourHours",
            "6h": "SixHours", "8h": "EightHours", "12h": "TwelveHours",
            "1d": "OneDay", "3d": "ThreeDays", "1w": "OneWeek", "1M": "OneMonth",
        }
        return mapping.get(self.TIME_FRAME, "OneHour")
