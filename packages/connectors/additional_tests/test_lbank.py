import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class LbankTester(AbstractExchangeTester):
    EXCHANGE_NAME = "lbank"
    SYMBOL = "BNB/USDT"
    ORDER_CURRENCY = "BNB"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 15


@pytest.mark.slow
@pytest.mark.asyncio
async def test_lbank_get_portfolio():
    await LbankTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_lbank_get_symbol_prices():
    await LbankTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_lbank_get_order_book():
    await LbankTester().test_get_order_book()


@pytest.mark.asyncio
async def test_lbank_get_recent_trades():
    await LbankTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_lbank_get_open_orders():
    await LbankTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_lbank_create_and_cancel_limit_order():
    await LbankTester().test_create_and_cancel_limit_order()
