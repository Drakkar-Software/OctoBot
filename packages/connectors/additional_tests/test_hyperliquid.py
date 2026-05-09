"""
Live hyperliquid integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_hyperliquid.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class HyperliquidTester(AbstractExchangeTester):
    EXCHANGE_NAME = "hyperliquid"
    SYMBOL = "BTC/USDC"
    SYMBOL_2 = "ETH/USDC"
    SYMBOL_3 = "HYPE/USDC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_hyperliquid_time_frames():
    await HyperliquidTester().test_time_frames()


@pytest.mark.asyncio
async def test_hyperliquid_get_market_status():
    await HyperliquidTester().test_get_market_status()


@pytest.mark.asyncio
async def test_hyperliquid_get_symbol_prices():
    await HyperliquidTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_hyperliquid_get_historical_symbol_prices():
    await HyperliquidTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_hyperliquid_get_kline_price():
    await HyperliquidTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_hyperliquid_get_order_book():
    await HyperliquidTester().test_get_order_book()


@pytest.mark.asyncio
async def test_hyperliquid_get_recent_trades():
    await HyperliquidTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_hyperliquid_get_price_ticker():
    await HyperliquidTester().test_get_price_ticker()
