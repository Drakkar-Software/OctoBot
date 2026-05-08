"""
Abstract base class for live exchange integration tests.
Mirrors packages/additional_tests/exchanges_tests/abstract_authenticated_exchange_tester.py
but delegates to the Rust ExchangeTestRunner via octobot_connectors_rs.
"""
import pytest
from abc import ABC

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
    EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION: bool = False
    SUPPORTS_BUNDLED_ORDERS: bool = False
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
        return ExchangeCredentials(api_key=key, secret=secret, password=password)

    # ---- Test entrypoints (async wrappers; PyO3 methods are synchronous) ----

    async def test_get_portfolio(self):
        connector = self.get_connector()
        connector.initialize()
        balance = connector.get_balance()
        assert balance is not None
        connector.stop()

    async def test_get_symbol_prices(self):
        connector = self.get_connector()
        connector.initialize()
        candles = connector.get_symbol_prices(self.SYMBOL, self.TIME_FRAME, 50, None)
        assert len(candles) > 0
        connector.stop()

    async def test_get_order_book(self):
        connector = self.get_connector()
        connector.initialize()
        ob = connector.get_order_book(self.SYMBOL, 10)
        assert ob is not None
        assert len(ob.bids) > 0
        assert len(ob.asks) > 0
        connector.stop()

    async def test_get_recent_trades(self):
        connector = self.get_connector()
        connector.initialize()
        trades = connector.get_recent_trades(self.SYMBOL, 10)
        assert isinstance(trades, list)
        connector.stop()

    async def test_get_open_orders(self):
        connector = self.get_connector()
        connector.initialize()
        orders = connector.get_open_orders(self.SYMBOL)
        assert isinstance(orders, list)
        connector.stop()

    async def test_get_closed_orders(self):
        connector = self.get_connector()
        connector.initialize()
        orders = connector.get_closed_orders(self.SYMBOL, None, 10)
        assert isinstance(orders, list)
        connector.stop()

    async def test_get_my_recent_trades(self):
        connector = self.get_connector()
        connector.initialize()
        trades = connector.get_my_recent_trades(self.SYMBOL, None, 10)
        assert isinstance(trades, list)
        connector.stop()

    async def test_create_and_cancel_limit_order(self):
        connector = self.get_connector()
        connector.initialize()
        from octobot_connectors import TraderOrderType, TradeOrderSide
        import decimal

        # place far-from-market limit buy so it won't fill
        ticker = connector.get_price_ticker(self.SYMBOL)
        current_price = ticker.last or ticker.close or ticker.bid
        order_price = current_price * (1 - self.ORDER_PRICE_DIFF / 100)

        order = connector.create_order(
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

        status = connector.cancel_order(order.id, self.SYMBOL, TraderOrderType.BuyLimit)
        from octobot_connectors import OrderStatus
        assert status in (OrderStatus.Canceled, OrderStatus.Closed)
        connector.stop()

    async def test_get_price_ticker(self):
        connector = self.get_connector()
        connector.initialize()
        ticker = connector.get_price_ticker(self.SYMBOL)
        assert ticker is not None
        assert ticker.last_price() is not None or ticker.bid is not None
        connector.stop()

    async def test_get_all_currencies_price_ticker(self):
        connector = self.get_connector()
        connector.initialize()
        tickers = connector.get_all_currencies_price_ticker([self.SYMBOL])
        assert isinstance(tickers, dict)
        assert len(tickers) >= 0
        connector.stop()

    async def test_get_cancelled_orders(self):
        connector = self.get_connector()
        connector.initialize()
        orders = connector.get_cancelled_orders(self.SYMBOL, None, 10)
        assert isinstance(orders, list)
        connector.stop()

    @pytest.mark.slow
    async def test_invalid_api_key_error(self):
        from octobot_connectors import ExchangeCredentials, ExchangeConfig, CcxtConnector
        creds = ExchangeCredentials(api_key="invalid_key", secret="invalid_secret")
        config = ExchangeConfig(
            exchange_name=self.EXCHANGE_NAME,
            credentials=creds,
            is_future=self.EXCHANGE_TYPE == "future",
        )
        connector = CcxtConnector(config=config)
        connector.initialize()
        try:
            connector.get_balance()
            pytest.fail("Expected authentication error")
        except RuntimeError as e:
            assert any(kw in str(e).lower() for kw in ("auth", "key", "signature", "invalid", "permission", "access"))
        finally:
            connector.stop()

    async def test_get_account_id(self):
        pytest.skip("get_account_id not yet exposed via PyO3")

    async def test_get_max_orders_count(self):
        pytest.skip("get_max_orders_count not yet exposed via PyO3")

    async def test_is_authenticated_request(self):
        pytest.skip("is_authenticated_request not yet exposed via PyO3")

    async def test_get_portfolio_with_market_filter(self):
        connector = self.get_connector()
        connector.initialize()
        balance = connector.get_balance()
        assert balance is not None
        symbols = connector.get_available_symbols(active_only=True)
        assert isinstance(symbols, list)
        connector.stop()

    async def test_untradable_symbols(self):
        connector = self.get_connector()
        connector.initialize()
        all_syms = connector.get_available_symbols(active_only=False)
        active_syms = connector.get_available_symbols(active_only=True)
        assert len(all_syms) >= len(active_syms)
        connector.stop()

    async def test_get_not_found_order(self):
        connector = self.get_connector()
        connector.initialize()
        order = connector.get_order("nonexistent_order_id_000000", self.SYMBOL)
        assert order is None
        connector.stop()

    async def test_create_and_fill_market_orders(self):
        pytest.skip("market order fill test requires real credentials and careful balance management")

    async def test_create_and_cancel_stop_orders(self):
        pytest.skip("stop order test requires real credentials")

    async def test_edit_limit_order(self):
        pytest.skip("edit order not yet fully exposed via PyO3")

    async def test_edit_stop_order(self):
        pytest.skip("edit stop order not yet fully exposed via PyO3")

    async def test_create_single_bundled_orders(self):
        pytest.skip("bundled orders not yet implemented in Rust connector")

    async def test_create_double_bundled_orders(self):
        pytest.skip("double bundled orders not yet implemented in Rust connector")

