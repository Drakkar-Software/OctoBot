import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class CoinbaseTester(AbstractExchangeTester):
    EXCHANGE_NAME = "coinbase"
    SYMBOL = "ADA/USDC"
    ORDER_CURRENCY = "ADA"
    SETTLEMENT_CURRENCY = "USDC"
    ORDER_SIZE = 70


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinbase_get_portfolio():
    await CoinbaseTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_coinbase_get_symbol_prices():
    await CoinbaseTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_coinbase_get_order_book():
    await CoinbaseTester().test_get_order_book()


@pytest.mark.asyncio
async def test_coinbase_get_recent_trades():
    await CoinbaseTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinbase_get_open_orders():
    await CoinbaseTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinbase_create_and_cancel_limit_order():
    await CoinbaseTester().test_create_and_cancel_limit_order()
