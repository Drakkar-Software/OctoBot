import pytest
from .abstract_exchange_tester import AbstractExchangeTester
from .abstract_future_exchange_tester import AbstractFutureExchangeTester

pytestmark = pytest.mark.asyncio


class BybitSpotTester(AbstractExchangeTester):
    EXCHANGE_NAME = "bybit"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 10


class BybitFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "bybit"
    SYMBOL = "BTC/USDT:USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 10


# ---- Spot ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_spot_get_portfolio():
    await BybitSpotTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_bybit_spot_get_symbol_prices():
    await BybitSpotTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_bybit_spot_get_order_book():
    await BybitSpotTester().test_get_order_book()


@pytest.mark.asyncio
async def test_bybit_spot_get_recent_trades():
    await BybitSpotTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_spot_get_open_orders():
    await BybitSpotTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_spot_create_and_cancel_limit_order():
    await BybitSpotTester().test_create_and_cancel_limit_order()


# ---- Futures ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_futures_get_portfolio():
    await BybitFuturesTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_bybit_futures_get_symbol_prices():
    await BybitFuturesTester().test_get_symbol_prices()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_futures_get_positions():
    await BybitFuturesTester().test_get_positions()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_futures_get_funding_rate():
    await BybitFuturesTester().test_get_funding_rate()
