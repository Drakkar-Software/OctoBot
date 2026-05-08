import pytest
from .abstract_exchange_tester import AbstractExchangeTester
from .abstract_future_exchange_tester import AbstractFutureExchangeTester

pytestmark = pytest.mark.asyncio


class KucoinSpotTester(AbstractExchangeTester):
    EXCHANGE_NAME = "kucoin"
    SYMBOL = "BTC/USDC"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDC"
    ORDER_SIZE = 50


class KucoinFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "kucoinfutures"
    SYMBOL = "DOT/USDT:USDT"
    ORDER_CURRENCY = "DOT"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 80


# ---- Spot ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_kucoin_spot_get_portfolio():
    await KucoinSpotTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_kucoin_spot_get_symbol_prices():
    await KucoinSpotTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_kucoin_spot_get_order_book():
    await KucoinSpotTester().test_get_order_book()


@pytest.mark.asyncio
async def test_kucoin_spot_get_recent_trades():
    await KucoinSpotTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kucoin_spot_get_open_orders():
    await KucoinSpotTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kucoin_spot_create_and_cancel_limit_order():
    await KucoinSpotTester().test_create_and_cancel_limit_order()


# ---- Futures ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_kucoin_futures_get_portfolio():
    await KucoinFuturesTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_kucoin_futures_get_symbol_prices():
    await KucoinFuturesTester().test_get_symbol_prices()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kucoin_futures_get_positions():
    await KucoinFuturesTester().test_get_positions()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kucoin_futures_get_funding_rate():
    await KucoinFuturesTester().test_get_funding_rate()
