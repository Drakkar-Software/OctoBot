"""
Abstract tester for futures exchanges.
Mirrors abstract_authenticated_future_exchange_tester.py
"""
from .abstract_exchange_tester import AbstractExchangeTester


class AbstractFutureExchangeTester(AbstractExchangeTester):
    EXCHANGE_TYPE: str = "future"
    SETTLEMENT_CURRENCY: str = "USDT"
    POSITION_SIDE: str = "long"
    DEFAULT_LEVERAGE: int = 1
    MARK_PRICE_IN_TICKER: bool = False

    async def test_get_positions(self):
        connector = self.get_connector()
        await connector.initialize()
        positions = await connector.get_positions([self.SYMBOL])
        assert isinstance(positions, list)
        await connector.stop()

    async def test_get_and_set_leverage(self):
        connector = self.get_connector()
        await connector.initialize()
        leverage_info = await connector.get_symbol_leverage(self.SYMBOL)
        assert leverage_info is not None

        new_lev = min((leverage_info.leverage or 1) + 1, 10)
        result = await connector.set_symbol_leverage(self.SYMBOL, float(new_lev), None)
        assert result is not None
        await connector.stop()

    async def test_set_margin_type(self):
        connector = self.get_connector()
        await connector.initialize()
        await connector.set_symbol_margin_type(self.SYMBOL, False, None)
        await connector.stop()

    async def test_get_funding_rate(self):
        connector = self.get_connector()
        await connector.initialize()
        rate = await connector.get_funding_rate(self.SYMBOL)
        assert rate is not None
        await connector.stop()

    async def test_get_mark_price(self):
        connector = self.get_connector()
        await connector.initialize()
        price = await connector.get_mark_price(self.SYMBOL)
        assert price is not None
        assert price > 0
        await connector.stop()
