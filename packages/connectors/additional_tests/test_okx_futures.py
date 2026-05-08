import pytest
from additional_tests.abstract_future_exchange_tester import AbstractFutureExchangeTester


class OkxFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "okx"
    EXCHANGE_TYPE = "future"
    SYMBOL = "BTC/USDT:USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"


@pytest.mark.asyncio
async def test_okx_futures_get_positions():
    await OkxFuturesTester().test_get_positions()


@pytest.mark.asyncio
async def test_okx_futures_get_and_set_leverage():
    await OkxFuturesTester().test_get_and_set_leverage()


@pytest.mark.asyncio
async def test_okx_futures_set_margin_type():
    await OkxFuturesTester().test_set_margin_type()


@pytest.mark.asyncio
async def test_okx_futures_get_funding_rate():
    await OkxFuturesTester().test_get_funding_rate()


@pytest.mark.asyncio
async def test_okx_futures_get_mark_price():
    await OkxFuturesTester().test_get_mark_price()
