"""
Live bingx integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_bingx.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class BingxTester(AbstractExchangeTester):
    EXCHANGE_NAME = "bingx"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "SHIB/USDT"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_bingx_time_frames():
    await BingxTester().test_time_frames()


@pytest.mark.asyncio
async def test_bingx_get_market_status():
    await BingxTester().test_get_market_status()


@pytest.mark.asyncio
async def test_bingx_get_symbol_prices():
    await BingxTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_bingx_get_historical_symbol_prices():
    await BingxTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_bingx_get_kline_price():
    await BingxTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_bingx_get_order_book():
    await BingxTester().test_get_order_book()


@pytest.mark.asyncio
async def test_bingx_get_recent_trades():
    await BingxTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_bingx_get_price_ticker():
    await BingxTester().test_get_price_ticker()
