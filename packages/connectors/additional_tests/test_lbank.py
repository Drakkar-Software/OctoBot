"""
Live lbank integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_lbank.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class LbankTester(AbstractExchangeTester):
    EXCHANGE_NAME = "lbank"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "DOGE/USDT"
    SYMBOL_3 = "SHIB/USDT"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_lbank_time_frames():
    await LbankTester().test_time_frames()


@pytest.mark.asyncio
async def test_lbank_get_market_status():
    await LbankTester().test_get_market_status()


@pytest.mark.asyncio
async def test_lbank_get_symbol_prices():
    await LbankTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_lbank_get_historical_symbol_prices():
    await LbankTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_lbank_get_kline_price():
    await LbankTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_lbank_get_order_book():
    await LbankTester().test_get_order_book()


@pytest.mark.asyncio
async def test_lbank_get_recent_trades():
    await LbankTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_lbank_get_price_ticker():
    await LbankTester().test_get_price_ticker()
