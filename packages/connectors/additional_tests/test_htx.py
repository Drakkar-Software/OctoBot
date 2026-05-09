"""
Live htx integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_htx.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class HtxTester(AbstractExchangeTester):
    EXCHANGE_NAME = "htx"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_htx_time_frames():
    await HtxTester().test_time_frames()


@pytest.mark.asyncio
async def test_htx_get_market_status():
    await HtxTester().test_get_market_status()


@pytest.mark.asyncio
async def test_htx_get_symbol_prices():
    await HtxTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_htx_get_historical_symbol_prices():
    await HtxTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_htx_get_kline_price():
    await HtxTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_htx_get_order_book():
    await HtxTester().test_get_order_book()


@pytest.mark.asyncio
async def test_htx_get_recent_trades():
    await HtxTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_htx_get_price_ticker():
    await HtxTester().test_get_price_ticker()
