"""
Live coinbase integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_coinbase_ed25519.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class CoinbaseEd25519Tester(AbstractExchangeTester):
    EXCHANGE_NAME = "coinbase"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "ADA/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_coinbase_ed25519_time_frames():
    await CoinbaseEd25519Tester().test_time_frames()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_market_status():
    await CoinbaseEd25519Tester().test_get_market_status()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_symbol_prices():
    await CoinbaseEd25519Tester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_historical_symbol_prices():
    await CoinbaseEd25519Tester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_kline_price():
    await CoinbaseEd25519Tester().test_get_kline_price()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_order_book():
    await CoinbaseEd25519Tester().test_get_order_book()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_recent_trades():
    await CoinbaseEd25519Tester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_price_ticker():
    await CoinbaseEd25519Tester().test_get_price_ticker()
