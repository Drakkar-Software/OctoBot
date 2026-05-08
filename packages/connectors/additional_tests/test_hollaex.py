import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class HollaexTester(AbstractExchangeTester):
    EXCHANGE_NAME = "hollaex"
    SYMBOL = "ETH/USDT"
    ORDER_CURRENCY = "ETH"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 5


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hollaex_get_portfolio():
    await HollaexTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_hollaex_get_symbol_prices():
    await HollaexTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_hollaex_get_order_book():
    await HollaexTester().test_get_order_book()


@pytest.mark.asyncio
async def test_hollaex_get_recent_trades():
    await HollaexTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hollaex_get_open_orders():
    await HollaexTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hollaex_create_and_cancel_limit_order():
    await HollaexTester().test_create_and_cancel_limit_order()
