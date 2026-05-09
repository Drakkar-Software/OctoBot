"""
Live gateio integration tests. Mirrors octobot_trading/tests_additional/real_exchanges/test_gateio.py
but uses the Rust connector via octobot_connectors.
"""
import pytest

from .abstract_exchange_tester import AbstractExchangeTester


class GateioTester(AbstractExchangeTester):
    EXCHANGE_NAME = "gateio"
    SYMBOL = "BTC/USDT"
    SYMBOL_2 = "ETH/BTC"
    SYMBOL_3 = "XRP/BTC"
    INACTIVE_MARKETS: list = []  # set to symbols expected to be inactive
    TIME_FRAME = "1h"


@pytest.mark.asyncio
async def test_gateio_time_frames():
    await GateioTester().test_time_frames()


@pytest.mark.asyncio
async def test_gateio_get_market_status():
    await GateioTester().test_get_market_status()


@pytest.mark.asyncio
async def test_gateio_get_symbol_prices():
    await GateioTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_gateio_get_historical_symbol_prices():
    await GateioTester().test_get_historical_symbol_prices()


@pytest.mark.asyncio
async def test_gateio_get_kline_price():
    await GateioTester().test_get_kline_price()


@pytest.mark.asyncio
async def test_gateio_get_order_book():
    await GateioTester().test_get_order_book()


@pytest.mark.asyncio
async def test_gateio_get_recent_trades():
    await GateioTester().test_get_recent_trades()


@pytest.mark.asyncio
async def test_gateio_get_price_ticker():
    await GateioTester().test_get_price_ticker()
