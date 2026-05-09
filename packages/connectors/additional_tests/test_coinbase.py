"""
Live coinbase integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_coinbase.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class CoinbaseTester(AbstractExchangeTester):
    EXCHANGE_NAME = "coinbase"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "ADA/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_coinbase_time_frames():
    await CoinbaseTester().test_time_frames()


@pytest.mark.asyncio
async def test_coinbase_get_market_status():
    await CoinbaseTester().test_get_market_status()


@pytest.mark.asyncio
async def test_coinbase_get_symbol_prices():
    await CoinbaseTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_coinbase_get_historical_symbol_prices():
    await CoinbaseTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_coinbase_get_kline_price():
    await CoinbaseTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_coinbase_get_order_book():
    await CoinbaseTester().test_get_order_book()


@pytest.mark.asyncio
async def test_coinbase_get_recent_trades():
    await CoinbaseTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_coinbase_get_price_ticker():
    await CoinbaseTester().test_get_price_ticker()
