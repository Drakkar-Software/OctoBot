import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class BitmartTester(AbstractExchangeTester):
    EXCHANGE_NAME = "bitmart"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 80


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bitmart_get_portfolio():
    await BitmartTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_bitmart_get_symbol_prices():
    await BitmartTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_bitmart_get_order_book():
    await BitmartTester().test_get_order_book()


@pytest.mark.asyncio
async def test_bitmart_get_recent_trades():
    await BitmartTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bitmart_get_open_orders():
    await BitmartTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bitmart_create_and_cancel_limit_order():
    await BitmartTester().test_create_and_cancel_limit_order()
