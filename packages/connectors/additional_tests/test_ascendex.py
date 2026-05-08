import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class AscendexTester(AbstractExchangeTester):
    EXCHANGE_NAME = "ascendex"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 30


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ascendex_get_portfolio():
    await AscendexTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_ascendex_get_symbol_prices():
    await AscendexTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_ascendex_get_order_book():
    await AscendexTester().test_get_order_book()


@pytest.mark.asyncio
async def test_ascendex_get_recent_trades():
    await AscendexTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ascendex_get_open_orders():
    await AscendexTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ascendex_create_and_cancel_limit_order():
    await AscendexTester().test_create_and_cancel_limit_order()
