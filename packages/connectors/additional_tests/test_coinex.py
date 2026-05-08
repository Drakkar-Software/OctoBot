import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class CoinexTester(AbstractExchangeTester):
    EXCHANGE_NAME = "coinex"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 90


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinex_get_portfolio():
    await CoinexTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_coinex_get_symbol_prices():
    await CoinexTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_coinex_get_order_book():
    await CoinexTester().test_get_order_book()


@pytest.mark.asyncio
async def test_coinex_get_recent_trades():
    await CoinexTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinex_get_open_orders():
    await CoinexTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinex_create_and_cancel_limit_order():
    await CoinexTester().test_create_and_cancel_limit_order()
