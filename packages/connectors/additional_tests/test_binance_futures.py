import pytest
from additional_tests.abstract_future_exchange_tester import AbstractFutureExchangeTester


class BinanceFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "binanceusdm"
    EXCHANGE_TYPE = "future"
    SYMBOL = "BTC/USDT:USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"


@pytest.mark.asyncio
async def test_binance_futures_get_positions():
    await BinanceFuturesTester().test_get_positions()


@pytest.mark.asyncio
async def test_binance_futures_get_and_set_leverage():
    await BinanceFuturesTester().test_get_and_set_leverage()


@pytest.mark.asyncio
async def test_binance_futures_set_margin_type():
    await BinanceFuturesTester().test_set_margin_type()


@pytest.mark.asyncio
async def test_binance_futures_get_funding_rate():
    await BinanceFuturesTester().test_get_funding_rate()


@pytest.mark.asyncio
async def test_binance_futures_get_mark_price():
    await BinanceFuturesTester().test_get_mark_price()
