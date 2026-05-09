"""
Live mexc integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_mexc.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class MexcTester(AbstractExchangeTester):
    EXCHANGE_NAME = "mexc"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_mexc_time_frames():
    await MexcTester().test_time_frames()


@pytest.mark.asyncio
async def test_mexc_get_market_status():
    await MexcTester().test_get_market_status()


@pytest.mark.asyncio
async def test_mexc_get_symbol_prices():
    await MexcTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_mexc_get_historical_symbol_prices():
    await MexcTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_mexc_get_kline_price():
    await MexcTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_mexc_get_order_book():
    await MexcTester().test_get_order_book()


@pytest.mark.asyncio
async def test_mexc_get_recent_trades():
    await MexcTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_mexc_get_price_ticker():
    await MexcTester().test_get_price_ticker()
