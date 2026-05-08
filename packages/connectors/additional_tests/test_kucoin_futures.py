import pytest
from additional_tests.abstract_future_exchange_tester import AbstractFutureExchangeTester


class KucoinFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "kucoinfutures"
    EXCHANGE_TYPE = "future"
    SYMBOL = "XBTUSDTM"
    ORDER_CURRENCY = "XBT"
    SETTLEMENT_CURRENCY = "USDT"


@pytest.mark.asyncio
async def test_kucoin_futures_get_positions():
    await KucoinFuturesTester().test_get_positions()


@pytest.mark.asyncio
async def test_kucoin_futures_get_and_set_leverage():
    await KucoinFuturesTester().test_get_and_set_leverage()


@pytest.mark.asyncio
async def test_kucoin_futures_set_margin_type():
    await KucoinFuturesTester().test_set_margin_type()


@pytest.mark.asyncio
async def test_kucoin_futures_get_funding_rate():
    await KucoinFuturesTester().test_get_funding_rate()


@pytest.mark.asyncio
async def test_kucoin_futures_get_mark_price():
    await KucoinFuturesTester().test_get_mark_price()
