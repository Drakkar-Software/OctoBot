import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class BingxTester(AbstractExchangeTester):
    EXCHANGE_NAME = "bingx"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 50


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bingx_get_portfolio():
    await BingxTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_bingx_get_symbol_prices():
    await BingxTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_bingx_get_order_book():
    await BingxTester().test_get_order_book()


@pytest.mark.asyncio
async def test_bingx_get_recent_trades():
    await BingxTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bingx_get_open_orders():
    await BingxTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bingx_create_and_cancel_limit_order():
    await BingxTester().test_create_and_cancel_limit_order()
