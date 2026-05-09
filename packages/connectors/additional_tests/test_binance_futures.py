"""
Live binanceusdm integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_binance_futures.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_future_exchange_tester import AbstractFutureExchangeTester


class BinanceFuturesTester(AbstractFutureExchangeTester):
    EXCHANGE_NAME = "binanceusdm"
    SYMBOL = "BTC/USDT:USDT"
    SYMBOL_2 = "ETH/USDT:USDT"
    SYMBOL_3 = "XRP/USDT:USDT"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_binance_futures_time_frames():
    await BinanceFuturesTester().test_time_frames()


@pytest.mark.asyncio
async def test_binance_futures_get_market_status():
    await BinanceFuturesTester().test_get_market_status()


@pytest.mark.asyncio
async def test_binance_futures_get_symbol_prices():
    await BinanceFuturesTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_binance_futures_get_historical_symbol_prices():
    await BinanceFuturesTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_binance_futures_get_kline_price():
    await BinanceFuturesTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_binance_futures_get_order_book():
    await BinanceFuturesTester().test_get_order_book()


@pytest.mark.asyncio
async def test_binance_futures_get_recent_trades():
    await BinanceFuturesTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_binance_futures_get_price_ticker():
    await BinanceFuturesTester().test_get_price_ticker()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_futures_get_funding_rate():
    await BinanceFuturesTester().test_get_funding_rate()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_futures_fetch_user_positions():
    await BinanceFuturesTester().test_fetch_user_positions()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_binance_futures_fetch_user_closed_positions():
    await BinanceFuturesTester().test_fetch_user_closed_positions()
