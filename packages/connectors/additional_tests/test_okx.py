"""
Live okx integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_okx.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class OkxTester(AbstractExchangeTester):
    EXCHANGE_NAME = "okx"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "OKB/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_okx_time_frames():
    await OkxTester().test_time_frames()


@pytest.mark.asyncio
async def test_okx_get_market_status():
    await OkxTester().test_get_market_status()


@pytest.mark.asyncio
async def test_okx_get_symbol_prices():
    await OkxTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_okx_get_historical_symbol_prices():
    await OkxTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_okx_get_kline_price():
    await OkxTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_okx_get_order_book():
    await OkxTester().test_get_order_book()


@pytest.mark.asyncio
async def test_okx_get_recent_trades():
    await OkxTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_okx_get_price_ticker():
    await OkxTester().test_get_price_ticker()
