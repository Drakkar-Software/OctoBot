"""
Live hollaex integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_hollaex.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class HollaexTester(AbstractExchangeTester):
    EXCHANGE_NAME = "hollaex"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/USDT"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1d"


@pytest.mark.asyncio
async def test_hollaex_time_frames():
    await HollaexTester().test_time_frames()


@pytest.mark.asyncio
async def test_hollaex_get_market_status():
    await HollaexTester().test_get_market_status()


@pytest.mark.asyncio
async def test_hollaex_get_symbol_prices():
    await HollaexTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_hollaex_get_historical_symbol_prices():
    await HollaexTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_hollaex_get_kline_price():
    await HollaexTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_hollaex_get_order_book():
    await HollaexTester().test_get_order_book()


@pytest.mark.asyncio
async def test_hollaex_get_recent_trades():
    await HollaexTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_hollaex_get_price_ticker():
    await HollaexTester().test_get_price_ticker()
