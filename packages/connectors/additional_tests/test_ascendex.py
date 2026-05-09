"""
Live ascendex integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_ascendex.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class AscendexTester(AbstractExchangeTester):
    EXCHANGE_NAME = "ascendex"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "BTT/USDT"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_ascendex_time_frames():
    await AscendexTester().test_time_frames()


@pytest.mark.asyncio
async def test_ascendex_get_market_status():
    await AscendexTester().test_get_market_status()


@pytest.mark.asyncio
async def test_ascendex_get_symbol_prices():
    await AscendexTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_ascendex_get_historical_symbol_prices():
    await AscendexTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_ascendex_get_kline_price():
    await AscendexTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_ascendex_get_order_book():
    await AscendexTester().test_get_order_book()


@pytest.mark.asyncio
async def test_ascendex_get_recent_trades():
    await AscendexTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_ascendex_get_price_ticker():
    await AscendexTester().test_get_price_ticker()
