"""
Abstract tester for options exchanges.
Mirrors packages/trading/tests_additional/real_exchanges/real_option_exchange_tester.py.
"""
from .abstract_future_exchange_tester import AbstractFutureExchangeTester


class AbstractOptionExchangeTester(AbstractFutureExchangeTester):
    EXCHANGE_TYPE: str = "option"
    MARKET_STATUS_TYPE: str = "option"
