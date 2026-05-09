"""
Live phemex integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_phemex.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class PhemexTester(AbstractExchangeTester):
    EXCHANGE_NAME = "phemex"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/USDT"
    SYMBOL_3 = "XRP/USDT"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_phemex_time_frames():
    await PhemexTester().test_time_frames()


@pytest.mark.asyncio
async def test_phemex_get_market_status():
    await PhemexTester().test_get_market_status()


@pytest.mark.asyncio
async def test_phemex_get_symbol_prices():
    await PhemexTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_phemex_get_historical_symbol_prices():
    await PhemexTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_phemex_get_kline_price():
    await PhemexTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_phemex_get_order_book():
    await PhemexTester().test_get_order_book()


@pytest.mark.asyncio
async def test_phemex_get_recent_trades():
    await PhemexTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_phemex_get_price_ticker():
    await PhemexTester().test_get_price_ticker()
