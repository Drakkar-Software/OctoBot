import pytest
from .abstract_exchange_tester import AbstractExchangeTester
from .abstract_future_exchange_tester import AbstractFutureExchangeTester

pytestmark = pytest.mark.asyncio


class OkxSpotTester(AbstractExchangeTester):
    EXCHANGE_NAME = "okx"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 50


class OkxFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "okx"
    SYMBOL = "DOT/USDT:USDT"
    ORDER_CURRENCY = "DOT"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 50


# ---- Spot ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_okx_spot_get_portfolio():
    await OkxSpotTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_okx_spot_get_symbol_prices():
    await OkxSpotTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_okx_spot_get_order_book():
    await OkxSpotTester().test_get_order_book()


@pytest.mark.asyncio
async def test_okx_spot_get_recent_trades():
    await OkxSpotTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_okx_spot_get_open_orders():
    await OkxSpotTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_okx_spot_create_and_cancel_limit_order():
    await OkxSpotTester().test_create_and_cancel_limit_order()


# ---- Futures ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_okx_futures_get_portfolio():
    await OkxFuturesTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_okx_futures_get_symbol_prices():
    await OkxFuturesTester().test_get_symbol_prices()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_okx_futures_get_positions():
    await OkxFuturesTester().test_get_positions()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_okx_futures_get_funding_rate():
    await OkxFuturesTester().test_get_funding_rate()
