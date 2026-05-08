import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class CryptocomTester(AbstractExchangeTester):
    EXCHANGE_NAME = "cryptocom"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 70


@pytest.mark.slow
@pytest.mark.asyncio
async def test_cryptocom_get_portfolio():
    await CryptocomTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_cryptocom_get_symbol_prices():
    await CryptocomTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_cryptocom_get_order_book():
    await CryptocomTester().test_get_order_book()


@pytest.mark.asyncio
async def test_cryptocom_get_recent_trades():
    await CryptocomTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_cryptocom_get_open_orders():
    await CryptocomTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_cryptocom_create_and_cancel_limit_order():
    await CryptocomTester().test_create_and_cancel_limit_order()
