import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class HyperliquidTester(AbstractExchangeTester):
    EXCHANGE_NAME = "hyperliquid"
    SYMBOL = "ETH/USDC"
    ORDER_CURRENCY = "ETH"
    SETTLEMENT_CURRENCY = "USDC"
    ORDER_SIZE = 25


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hyperliquid_get_portfolio():
    await HyperliquidTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_hyperliquid_get_symbol_prices():
    await HyperliquidTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_hyperliquid_get_order_book():
    await HyperliquidTester().test_get_order_book()


@pytest.mark.asyncio
async def test_hyperliquid_get_recent_trades():
    await HyperliquidTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hyperliquid_get_open_orders():
    await HyperliquidTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_hyperliquid_create_and_cancel_limit_order():
    await HyperliquidTester().test_create_and_cancel_limit_order()
