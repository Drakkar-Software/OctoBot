import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class MexcTester(AbstractExchangeTester):
    EXCHANGE_NAME = "mexc"
    SYMBOL = "MX/USDT"
    ORDER_CURRENCY = "MX"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 70


@pytest.mark.slow
@pytest.mark.asyncio
async def test_mexc_get_portfolio():
    await MexcTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_mexc_get_symbol_prices():
    await MexcTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_mexc_get_order_book():
    await MexcTester().test_get_order_book()


@pytest.mark.asyncio
async def test_mexc_get_recent_trades():
    await MexcTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_mexc_get_open_orders():
    await MexcTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_mexc_create_and_cancel_limit_order():
    await MexcTester().test_create_and_cancel_limit_order()
