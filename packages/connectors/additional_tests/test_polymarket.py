"""
Live polymarket integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_polymarket.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class PolymarketTester(AbstractExchangeTester):
    EXCHANGE_NAME = "polymarket"
    SYMBOL = "PLACEHOLDER/USDC"
    SYMBOL_2 = "PLACEHOLDER2/USDC"
    SYMBOL_3 = "PLACEHOLDER3/USDC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1m"


@pytest.mark.asyncio
async def test_polymarket_time_frames():
    await PolymarketTester().test_time_frames()


@pytest.mark.asyncio
async def test_polymarket_get_market_status():
    await PolymarketTester().test_get_market_status()


@pytest.mark.asyncio
async def test_polymarket_get_symbol_prices():
    await PolymarketTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_polymarket_get_historical_symbol_prices():
    await PolymarketTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_polymarket_get_kline_price():
    await PolymarketTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_polymarket_get_order_book():
    await PolymarketTester().test_get_order_book()


@pytest.mark.asyncio
async def test_polymarket_get_recent_trades():
    await PolymarketTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_polymarket_get_price_ticker():
    await PolymarketTester().test_get_price_ticker()
