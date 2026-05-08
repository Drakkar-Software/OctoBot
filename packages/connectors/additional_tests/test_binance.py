"""
Live Binance integration tests.
Requires BINANCE_API_KEY and BINANCE_API_SECRET environment variables.
Run with: pytest additional_tests/test_binance.py -v -m "not slow"
"""
import asyncio
import pytest

from .abstract_exchange_tester import AbstractExchangeTester
from .abstract_future_exchange_tester import AbstractFutureExchangeTester


class BinanceSpotTester(AbstractExchangeTester):
    EXCHANGE_NAME = "binance"
    EXCHANGE_TYPE = "spot"
    SYMBOL = "BTC/USDT"
    TIME_FRAME = "1h"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 5
    ORDER_PRICE_DIFF = 10


class BinanceFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "binanceusdm"
    EXCHANGE_TYPE = "future"
    SYMBOL = "BTC/USDT:USDT"
    TIME_FRAME = "1h"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 5
    ORDER_PRICE_DIFF = 10


# ---- Spot tests ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_spot_get_portfolio():
    await BinanceSpotTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_binance_spot_get_symbol_prices():
    await BinanceSpotTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_binance_spot_get_order_book():
    await BinanceSpotTester().test_get_order_book()


@pytest.mark.asyncio
async def test_binance_spot_get_recent_trades():
    await BinanceSpotTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_spot_get_open_orders():
    await BinanceSpotTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_spot_create_and_cancel_limit_order():
    await BinanceSpotTester().test_create_and_cancel_limit_order()


# ---- Futures tests ----

@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_futures_get_portfolio():
    await BinanceFuturesTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_binance_futures_get_symbol_prices():
    await BinanceFuturesTester().test_get_symbol_prices()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_futures_get_positions():
    await BinanceFuturesTester().test_get_positions()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_futures_get_funding_rate():
    await BinanceFuturesTester().test_get_funding_rate()
