"""
Live bybit integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_bybit_futures.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_future_exchange_tester import AbstractFutureExchangeTester


class BybitFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "bybit"
    SYMBOL = "BTC/USDT:USDT"
    SYMBOL_2 = "ETH/USDT:USDT"
    SYMBOL_3 = "XRP/USDT:USDT"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_bybit_futures_time_frames():
    await BybitFuturesTester().test_time_frames()


@pytest.mark.asyncio
async def test_bybit_futures_get_market_status():
    await BybitFuturesTester().test_get_market_status()


@pytest.mark.asyncio
async def test_bybit_futures_get_symbol_prices():
    await BybitFuturesTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_bybit_futures_get_historical_symbol_prices():
    await BybitFuturesTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_bybit_futures_get_kline_price():
    await BybitFuturesTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_bybit_futures_get_order_book():
    await BybitFuturesTester().test_get_order_book()


@pytest.mark.asyncio
async def test_bybit_futures_get_recent_trades():
    await BybitFuturesTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_bybit_futures_get_price_ticker():
    await BybitFuturesTester().test_get_price_ticker()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_futures_get_funding_rate():
    await BybitFuturesTester().test_get_funding_rate()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_futures_fetch_user_positions():
    await BybitFuturesTester().test_fetch_user_positions()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bybit_futures_fetch_user_closed_positions():
    await BybitFuturesTester().test_fetch_user_closed_positions()
