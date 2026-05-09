"""
Live cryptocom integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_cryptocom.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class CryptocomTester(AbstractExchangeTester):
    EXCHANGE_NAME = "cryptocom"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_cryptocom_time_frames():
    await CryptocomTester().test_time_frames()


@pytest.mark.asyncio
async def test_cryptocom_get_market_status():
    await CryptocomTester().test_get_market_status()


@pytest.mark.asyncio
async def test_cryptocom_get_symbol_prices():
    await CryptocomTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_cryptocom_get_historical_symbol_prices():
    await CryptocomTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_cryptocom_get_kline_price():
    await CryptocomTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_cryptocom_get_order_book():
    await CryptocomTester().test_get_order_book()


@pytest.mark.asyncio
async def test_cryptocom_get_recent_trades():
    await CryptocomTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_cryptocom_get_price_ticker():
    await CryptocomTester().test_get_price_ticker()
