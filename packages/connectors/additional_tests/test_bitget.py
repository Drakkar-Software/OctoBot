import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class BitgetTester(AbstractExchangeTester):
    EXCHANGE_NAME = "bitget"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 40


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bitget_get_portfolio():
    await BitgetTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_bitget_get_symbol_prices():
    await BitgetTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_bitget_get_order_book():
    await BitgetTester().test_get_order_book()


@pytest.mark.asyncio
async def test_bitget_get_recent_trades():
    await BitgetTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bitget_get_open_orders():
    await BitgetTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bitget_create_and_cancel_limit_order():
    await BitgetTester().test_create_and_cancel_limit_order()
