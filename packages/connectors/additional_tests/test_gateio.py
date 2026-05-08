import pytest
from .abstract_exchange_tester import AbstractExchangeTester

pytestmark = pytest.mark.asyncio


class GateioTester(AbstractExchangeTester):
    EXCHANGE_NAME = "gateio"
    SYMBOL = "BTC/USDT"
    ORDER_CURRENCY = "BTC"
    SETTLEMENT_CURRENCY = "USDT"
    ORDER_SIZE = 40


@pytest.mark.slow
@pytest.mark.asyncio
async def test_gateio_get_portfolio():
    await GateioTester().test_get_portfolio()


@pytest.mark.asyncio
async def test_gateio_get_symbol_prices():
    await GateioTester().test_get_symbol_prices()


@pytest.mark.asyncio
async def test_gateio_get_order_book():
    await GateioTester().test_get_order_book()


@pytest.mark.asyncio
async def test_gateio_get_recent_trades():
    await GateioTester().test_get_recent_trades()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_gateio_get_open_orders():
    await GateioTester().test_get_open_orders()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_gateio_create_and_cancel_limit_order():
    await GateioTester().test_create_and_cancel_limit_order()
