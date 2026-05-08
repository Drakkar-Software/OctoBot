import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class PhemexTester(AbstractExchangeTester):
    EXCHANGE_NAME = "phemex"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 10


@pytest.mark.slow
@pytest.mark.asyncio
async def test_phemex_get_portfolio():
    await PhemexTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_phemex_get_symbol_prices():
    await PhemexTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_phemex_get_order_book():
    await PhemexTester().test_get_order_book()


@pytest.mark.asyncio
async def test_phemex_get_recent_trades():
    await PhemexTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_phemex_get_open_orders():
    await PhemexTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_phemex_create_and_cancel_limit_order():
    await PhemexTester().test_create_and_cancel_limit_order()
