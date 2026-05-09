"""
Live bitmart integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_bitmart.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class BitmartTester(AbstractExchangeTester):
    EXCHANGE_NAME = "bitmart"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "TRX/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_bitmart_time_frames():
    await BitmartTester().test_time_frames()


@pytest.mark.asyncio
async def test_bitmart_get_market_status():
    await BitmartTester().test_get_market_status()


@pytest.mark.asyncio
async def test_bitmart_get_symbol_prices():
    await BitmartTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_bitmart_get_historical_symbol_prices():
    await BitmartTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_bitmart_get_kline_price():
    await BitmartTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_bitmart_get_order_book():
    await BitmartTester().test_get_order_book()


@pytest.mark.asyncio
async def test_bitmart_get_recent_trades():
    await BitmartTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_bitmart_get_price_ticker():
    await BitmartTester().test_get_price_ticker()
