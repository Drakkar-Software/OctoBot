import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class HtxTester(AbstractExchangeTester):
    EXCHANGE_NAME = "htx"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 50


@pytest.mark.slow
@pytest.mark.asyncio
async def test_htx_get_portfolio():
    await HtxTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_htx_get_symbol_prices():
    await HtxTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_htx_get_order_book():
    await HtxTester().test_get_order_book()


@pytest.mark.asyncio
async def test_htx_get_recent_trades():
    await HtxTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_htx_get_open_orders():
    await HtxTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_htx_create_and_cancel_limit_order():
    await HtxTester().test_create_and_cancel_limit_order()
