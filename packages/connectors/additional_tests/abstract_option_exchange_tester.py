"""
Abstract tester for options exchanges.
Mirrors abstract_authenticated_option_exchange_tester.py
"""
from .abstract_exchange_tester import AbstractExchangeTester


class AbstractOptionExchangeTester(AbstractExchangeTester):
    EXCHANGE_TYPE: str = "option"
    OPTION_EXPIRY: str = ""   # override with actual expiry date
    OPTION_STRIKE: float = 0.0
    OPTION_TYPE: str = "call"  # or "put"

    async def test_get_option_positions(self):
        connector = self.get_connector()
        await connector.initialize()
        positions = await connector.get_positions(None)
        assert isinstance(positions, list)
        await connector.stop()
