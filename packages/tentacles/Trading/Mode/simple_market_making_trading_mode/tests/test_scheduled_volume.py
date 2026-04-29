# Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import uuid
import mock
import pytest
import decimal
import asyncio
import time
import random

import octobot_trading.api
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.symbols as symbols
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as personal_data
import tentacles.Trading.Mode.simple_market_making_trading_mode.scheduled_volume as scheduled_volume_import


@pytest.fixture
def exchange_manager_mock():
    class ExchangeManagerMock:
        def __init__(self):
            self.id = str(uuid.uuid4())
            self.exchange_name = "test_exchange"
            self.is_future = False
            self.open_orders = []
            self.exchange = mock.Mock(
                get_exchange_current_time=mock.Mock(return_value=time.time())
            )
            self.trader = mock.Mock(
                exchange_manager=self
            )
            self.exchange_personal_data = mock.Mock(
                orders_manager=mock.Mock(
                    get_open_orders=mock.Mock(return_value=self.open_orders)
                )
            )
            self.get_exchange_quote_and_base = mock.Mock(return_value=("BTC", "USDT"))

    return ExchangeManagerMock()


@pytest.fixture
def scheduled_volume(exchange_manager_mock):
    return scheduled_volume_import.ScheduledVolume(
        exchange_manager=exchange_manager_mock,
        symbol="BTC/USDT",
        on_missing_funds_callback=mock.AsyncMock(),
        min_interval=1.0,
        max_interval=5.0,
        min_quote_amount=100,
        max_quote_amount=1000
    )


@pytest.fixture
def portfolio_mock():
    class CurrencyPortfolioMock:
        def __init__(self, available):
            self.available = available

    return CurrencyPortfolioMock


@pytest.mark.asyncio
async def test_initialization(scheduled_volume):
    assert scheduled_volume.symbol == "BTC/USDT"
    assert isinstance(scheduled_volume.parsed_symbol, symbols.Symbol)
    assert scheduled_volume.min_interval == 1.0
    assert scheduled_volume.max_interval == 5.0
    assert scheduled_volume.min_quote_amount == 100.0
    assert scheduled_volume.max_quote_amount == 1000.0
    assert scheduled_volume._healthy is False
    assert scheduled_volume._should_stop is False
    assert scheduled_volume._task is None
    assert scheduled_volume._last_order_side == trading_enums.TradeOrderSide.SELL
    assert scheduled_volume._last_on_missing_funds_callback_call_time == 0
    assert isinstance(scheduled_volume._on_missing_funds_callback, mock.AsyncMock)


def test_validate_parameters_valid(scheduled_volume):
    scheduled_volume._validate_parameters()  # Should not raise any exception


def test_validate_parameters_invalid_interval(exchange_manager_mock):
    with pytest.raises(ValueError, match="`min_interval` must be greater or equal to `max_interval`"):
        scheduled_volume_import.ScheduledVolume(
            exchange_manager=exchange_manager_mock,
            symbol="BTC/USDT",
            on_missing_funds_callback=mock.AsyncMock(),
            min_interval=5.0,  # Greater than max_interval
            max_interval=1.0,
            min_quote_amount=100,
            max_quote_amount=1000
        )._validate_parameters()


def test_validate_parameters_invalid_quote_amount(exchange_manager_mock):
    with pytest.raises(ValueError, match="`min_quote_amount` must be greater or equal to `max_quote_amount`"):
        scheduled_volume_import.ScheduledVolume(
            exchange_manager=exchange_manager_mock,
            symbol="BTC/USDT",
            on_missing_funds_callback=mock.AsyncMock(),
            min_interval=1.0,
            max_interval=5.0,
            min_quote_amount=1000,  # Greater than max_quote_amount
            max_quote_amount=100
        )._validate_parameters()


def test_get_total_locked_funds_quote_value(scheduled_volume):
    # Set some test values
    scheduled_volume._update_locked_funds(decimal.Decimal("2"), decimal.Decimal("1000"))
    current_price = decimal.Decimal("30000.1")

    result = scheduled_volume._get_total_locked_funds_quote_value(current_price)

    assert result == decimal.Decimal("61000.2")  # 1000 + (2 * 30000)


def test_should_reset_locked_funds(scheduled_volume):
    current_price = decimal.Decimal("30000.01")
    scheduled_volume._update_locked_funds(decimal.Decimal("0.01"), decimal.Decimal("100"))

    # Total locked value (400) < max_quote_amount (1000)
    # 100 + (0.01 * 30000) = 400
    assert scheduled_volume._should_reset_locked_funds(current_price) is True

    # Set higher locked values
    scheduled_volume._update_locked_funds(decimal.Decimal("0.1"), decimal.Decimal("2000"))
    # Total locked value (5000) > max_quote_amount (1000)
    # 2000 + (0.1 * 30000) = 5000
    assert scheduled_volume._should_reset_locked_funds(current_price) is False


def test_get_sleeping_time(scheduled_volume):
    # Test multiple times to ensure the random value is within bounds
    for _ in range(100):
        sleep_time = scheduled_volume._get_sleeping_time()
        assert scheduled_volume.min_interval <= sleep_time <= scheduled_volume.max_interval


@pytest.mark.asyncio
async def test_stop(scheduled_volume):
    scheduled_volume._task = asyncio.create_task(asyncio.sleep(1))
    scheduled_volume.stop()
    assert scheduled_volume._should_stop is True
    assert scheduled_volume._task is None


def test_clear(scheduled_volume):
    scheduled_volume.clear()
    assert scheduled_volume.exchange_manager is None
    assert scheduled_volume._on_missing_funds_callback is None


def test_get_global_locked_funds():
    exchange_id = "test_id"
    scheduled_volume_import._LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_id] = {
        "BTC/USDT": {
            "BTC": decimal.Decimal("1.5"),
            "USDT": decimal.Decimal("45000")
        },
        "ETH/USDT": {
            "ETH": decimal.Decimal("10"),
            "USDT": decimal.Decimal("20000")
        }
    }

    # Test getting locked funds for BTC excluding BTC/USDT
    btc_locked = scheduled_volume_import.get_global_locked_funds(exchange_id, "BTC", "BTC/USDT")
    assert btc_locked == decimal.Decimal("0")

    # Test getting locked funds for USDT excluding BTC/USDT
    usdt_locked = scheduled_volume_import.get_global_locked_funds(exchange_id, "USDT", "BTC/USDT")
    assert usdt_locked == decimal.Decimal("20000")


def test_reset_locked_funds_invalid_price(scheduled_volume):
    # Test with zero or negative price
    assert scheduled_volume._reset_locked_funds(trading_constants.ZERO) is None
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert locked_base == trading_constants.ZERO
    assert locked_quote == trading_constants.ZERO


@mock.patch('octobot_trading.api.get_portfolio_currency')
def test_reset_locked_funds_base_heavy_portfolio(mock_get_portfolio, portfolio_mock, scheduled_volume):
    current_price = decimal.Decimal("50000")  # BTC/USDT price

    # Mock portfolio with more value in base currency (BTC)
    mock_get_portfolio.side_effect = [
        portfolio_mock(decimal.Decimal("1")),  # BTC available
        portfolio_mock(decimal.Decimal("10000"))  # USDT available
    ]

    action = scheduled_volume._reset_locked_funds(current_price)

    assert action is None
    # Should lock more base currency since portfolio has more value in base
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert locked_base == decimal.Decimal("0.04")
    assert locked_quote == decimal.Decimal("0")


@mock.patch('octobot_trading.api.get_portfolio_currency')
def test_reset_locked_funds_quote_heavy_portfolio(mock_get_portfolio, portfolio_mock, scheduled_volume):
    current_price = decimal.Decimal("50000")  # BTC/USDT price

    # Mock portfolio with more value in quote currency (USDT)
    mock_get_portfolio.side_effect = [
        portfolio_mock(decimal.Decimal("0.1")),  # BTC available
        portfolio_mock(decimal.Decimal("100000"))  # USDT available
    ]

    action = scheduled_volume._reset_locked_funds(current_price)

    assert action is None
    # Should lock more quote currency since portfolio has more value in quote
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert locked_base == decimal.Decimal("0")
    assert locked_quote == decimal.Decimal("2000")  # all taken from available quote (largest holding)


@mock.patch('octobot_trading.api.get_portfolio_currency')
def test_reset_locked_funds_insufficient_funds(mock_get_portfolio, portfolio_mock, scheduled_volume):
    current_price = decimal.Decimal("50000")  # BTC/USDT price

    # Mock portfolio with very low balances
    mock_get_portfolio.side_effect = [
        portfolio_mock(decimal.Decimal("0.0001")),  # BTC available
        portfolio_mock(decimal.Decimal("1"))  # USDT available
    ]

    action = scheduled_volume._reset_locked_funds(current_price)

    assert action is None
    # Should lock whatever small amount is available
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert trading_constants.ZERO < locked_base <= decimal.Decimal("0.0001")
    assert trading_constants.ZERO < locked_quote <= decimal.Decimal("1")


@mock.patch('octobot_trading.api.get_portfolio_currency')
def test_reset_locked_funds_with_open_orders_more_sell_orders(mock_get_portfolio, portfolio_mock, scheduled_volume):
    current_price = decimal.Decimal("50000")

    # Mock portfolio with low balances
    mock_get_portfolio.side_effect = [
        portfolio_mock(decimal.Decimal("0.000001")),  # BTC available
        portfolio_mock(decimal.Decimal("0.000001"))  # USDT available
    ]

    # Create mock orders
    sell_1 = personal_data.SellLimitOrder(scheduled_volume.exchange_manager.trader)
    sell_1.update(
        order_type=trading_enums.TraderOrderType.SELL_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.001"),
        price=decimal.Decimal("25000")
    )
    sell_2 = personal_data.SellLimitOrder(scheduled_volume.exchange_manager.trader)
    sell_2.update(
        order_type=trading_enums.TraderOrderType.SELL_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.002"),
        price=decimal.Decimal("25000")
    )
    buy_1 = personal_data.BuyLimitOrder(scheduled_volume.exchange_manager.trader)
    buy_1.update(
        order_type=trading_enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.004"),
        price=decimal.Decimal("20000")
    )
    open_orders = [sell_1, sell_2, buy_1]

    # Mock the orders manager
    scheduled_volume.exchange_manager.open_orders.extend(open_orders)

    action = scheduled_volume._reset_locked_funds(current_price)

    scheduled_volume.exchange_manager.exchange_personal_data.orders_manager.get_open_orders.assert_called_once_with("BTC/USDT")

    assert action is None   # not enough funds to cover all required funds: no need to rebalance
    # Should include funds from portfolio as cancelling ordes won't help
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert locked_base == decimal.Decimal("0.000001")
    assert locked_quote == decimal.Decimal("0.000001")


@mock.patch('octobot_trading.api.get_portfolio_currency')
def test_reset_locked_funds_with_open_orders_more_buy_orders_with_cancel_open_order(mock_get_portfolio, portfolio_mock, scheduled_volume):
    current_price = decimal.Decimal("50000")

    # Mock portfolio with low balances
    mock_get_portfolio.side_effect = [
        portfolio_mock(decimal.Decimal("0.000001")),  # BTC available
        portfolio_mock(decimal.Decimal("0.000001"))  # USDT available
    ]

    # Create mock orders
    sell_1 = personal_data.SellLimitOrder(scheduled_volume.exchange_manager.trader)
    sell_1.update(
        order_type=trading_enums.TraderOrderType.SELL_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.01"),
        price=decimal.Decimal("25000")
    )
    sell_2 = personal_data.SellLimitOrder(scheduled_volume.exchange_manager.trader)
    sell_2.update(
        order_type=trading_enums.TraderOrderType.SELL_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.014"),
        price=decimal.Decimal("25000")
    )
    buy_1 = personal_data.BuyLimitOrder(scheduled_volume.exchange_manager.trader)
    buy_1.update(
        order_type=trading_enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.07"),
        price=decimal.Decimal("20000")
    )
    open_orders = [sell_1, sell_2, buy_1]

    # Mock the orders manager
    scheduled_volume.exchange_manager.open_orders.extend(open_orders)

    action = scheduled_volume._reset_locked_funds(current_price)

    scheduled_volume.exchange_manager.exchange_personal_data.orders_manager.get_open_orders.assert_called_once_with("BTC/USDT")

    assert action == scheduled_volume_import.LockFundsActions.REALLOCATE_SCHEDULED_VOLUME_FUNDS
    # Should include funds from all open orders in locked amounts
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert locked_base == decimal.Decimal("0.01199999998")
    assert locked_quote == decimal.Decimal("1400.000001")


@mock.patch('octobot_trading.api.get_portfolio_currency')
def test_reset_locked_funds_zero_balance(mock_get_portfolio, portfolio_mock, scheduled_volume):
    current_price = decimal.Decimal("50000")

    # Mock portfolio with zero balances
    mock_get_portfolio.side_effect = [
        portfolio_mock(decimal.Decimal("0")),  # BTC available
        portfolio_mock(decimal.Decimal("0"))  # USDT available
    ]

    action = scheduled_volume._reset_locked_funds(current_price)

    assert action is None
    # Should not lock any funds
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert locked_base == trading_constants.ZERO
    assert locked_quote == trading_constants.ZERO


@mock.patch('octobot_trading.api.get_portfolio_currency')
def test_reset_locked_funds_existing_global_locks(mock_get_portfolio, portfolio_mock, scheduled_volume):
    current_price = decimal.Decimal("50000")

    # Set up existing global locked funds
    scheduled_volume_import._LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {
        "BTC/USDT": {
            "BTC": decimal.Decimal("0.1"),
            "USDT": decimal.Decimal("5000")
        }
    }

    # Mock portfolio
    mock_get_portfolio.side_effect = [
        portfolio_mock(decimal.Decimal("1")),  # BTC available
        portfolio_mock(decimal.Decimal("50000"))  # USDT available
    ]

    action = scheduled_volume._reset_locked_funds(current_price)

    assert action is None
    # Should consider existing locked funds when calculating new locks
    locked_base, locked_quote = scheduled_volume._get_locked_base_and_quote()
    assert locked_base == decimal.Decimal("0.1")
    assert locked_quote == decimal.Decimal("5000")
    # Clean up global state
    scheduled_volume_import._LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()


@pytest.mark.asyncio
async def test_wait_required_locked_funds_init_no_waiting_required(scheduled_volume):
    # Clear any existing data
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {}

    with mock.patch.object(asyncio, "wait_for", wraps=asyncio.wait_for) as mock_wait_for:
        # Test when no initialization is required (empty state)
        await scheduled_volume.wait_required_locked_funds_init()
        mock_wait_for.assert_not_called()


@pytest.mark.asyncio
async def test_wait_required_locked_funds_init_immediate_completion(scheduled_volume):
    # Clear any existing data
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {}

    # Set up an already completed event
    event = asyncio.Event()
    event.set()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id]["BTC/USDT"] = event

    with mock.patch.object(asyncio, "wait_for", wraps=asyncio.wait_for) as mock_wait_for:
        await scheduled_volume.wait_required_locked_funds_init()
        mock_wait_for.assert_not_called()


@pytest.mark.asyncio
async def test_wait_required_locked_funds_init_timeout(scheduled_volume):
    # Clear any existing data
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {}

    # Set up an event that will never be set
    event = asyncio.Event()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id]["BTC/USDT"] = event

    # does not raise
    with mock.patch.object(asyncio, "wait_for", mock.AsyncMock(side_effect=asyncio.TimeoutError)) as mock_wait_for:
        await scheduled_volume.wait_required_locked_funds_init()
    mock_wait_for.assert_called_once()


@pytest.mark.asyncio
async def test_wait_required_locked_funds_init_multiple_pairs(scheduled_volume):
    # Clear any existing data
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {}

    # Set up events for multiple trading pairs
    btc_event = asyncio.Event()
    eth_event = asyncio.Event()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id].update({
        "BTC/USDT": btc_event,
        "ETH/USDT": eth_event
    })

    # Set up a task to set the events after a short delay
    async def set_events():
        await asyncio_tools.wait_asyncio_next_cycle()
        btc_event.set()
        eth_event.set()

    # Start the background task
    asyncio.create_task(set_events())

    with mock.patch.object(asyncio, "wait_for", wraps=asyncio.wait_for) as mock_wait_for:
        await scheduled_volume.wait_required_locked_funds_init()
        mock_wait_for.assert_called_once()


@pytest.mark.asyncio
async def test_wait_required_locked_funds_init_related_pairs(scheduled_volume):
    # Clear any existing data
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {}

    # Set up events for pairs that share currencies
    event_1 = asyncio.Event()
    event_2 = asyncio.Event()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id].update({
        "BTC/SOL": event_1,
        "ETH/USDT": event_2
    })

    # Set up a task to set the events after a short delay
    async def set_events():
        await asyncio_tools.wait_asyncio_next_cycle()
        event_1.set()
        event_2.set()

    # Start the background task
    asyncio.create_task(set_events())

    with mock.patch.object(asyncio, "wait_for", wraps=asyncio.wait_for) as mock_wait_for:
        await scheduled_volume.wait_required_locked_funds_init()
        mock_wait_for.assert_called_once()


@pytest.mark.asyncio
async def test_wait_required_locked_funds_init_unrelated_pairs(scheduled_volume):
    # Clear any existing data
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {}

    # Set up events for unrelated trading pairs
    eth_usdt_event = asyncio.Event()
    xrp_usdt_event = asyncio.Event()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id].update({
        "ETH/SOL": eth_usdt_event,
        "XRP/PLOP": xrp_usdt_event
    })

    # These pairs are unrelated to BTC/USDT, so should not wait
    with mock.patch.object(asyncio, "wait_for", wraps=asyncio.wait_for) as mock_wait_for:
        await scheduled_volume.wait_required_locked_funds_init()
        mock_wait_for.assert_not_called()


@pytest.mark.asyncio
async def test_wait_required_locked_funds_init_partial_completion(scheduled_volume):
    # Clear any existing data
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID.clear()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id] = {}

    # Set up events for multiple related pairs
    btc_usdt_event = asyncio.Event()
    eth_usdt_event = asyncio.Event()
    scheduled_volume_import._INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[scheduled_volume.exchange_manager.id].update({
        "BTC/USDT": btc_usdt_event,
        "ETH/USDT": eth_usdt_event
    })

    # Only set one event
    btc_usdt_event.set()

    # Set up a task to set the events after a short delay
    async def set_events():
        await asyncio_tools.wait_asyncio_next_cycle()
        eth_usdt_event.set()

    # Start the background task
    asyncio.create_task(set_events())

    with mock.patch.object(asyncio, "wait_for", wraps=asyncio.wait_for) as mock_wait_for:
        await scheduled_volume.wait_required_locked_funds_init()
        # called to wait for eth_usdt_event
        mock_wait_for.assert_called_once()


@pytest.mark.asyncio
async def test_schedule_loop(scheduled_volume):
    async def _wait_asyncio_next_cycle_wrapper(*args):
        await asyncio_tools.wait_asyncio_next_cycle()
    # no current price
    with mock.patch.object(
        scheduled_volume, '_initialize_locked_funds', mock.AsyncMock()
    ) as _initialize_locked_funds_mock, mock.patch.object(
        scheduled_volume, '_update_locked_funds_from_last_orders_trades', mock.Mock(return_value=[])
    ) as _update_locked_funds_from_last_orders_trades_mock, mock.patch.object(
        asyncio, 'sleep', mock.AsyncMock(side_effect=_wait_asyncio_next_cycle_wrapper)
    ) as sleep_mock:
        with mock.patch.object(
            scheduled_volume, '_trigger', mock.AsyncMock(return_value=[])
        ) as _trigger_mock:
            schedule_loop_task = asyncio.create_task(scheduled_volume._schedule_loop())
            # did not run yet
            _initialize_locked_funds_mock.assert_not_called()
            _trigger_mock.assert_not_called()
            _update_locked_funds_from_last_orders_trades_mock.assert_not_called()
            sleep_mock.assert_not_called()
            # wait for a cycle
            await asyncio_tools.wait_asyncio_next_cycle()
            # 1 cycle triggered
            _initialize_locked_funds_mock.assert_called_once()
            _trigger_mock.assert_called_once()
            _update_locked_funds_from_last_orders_trades_mock.assert_called_once_with([])
            sleep_mock.assert_called_once()
            _initialize_locked_funds_mock.reset_mock()
            _trigger_mock.reset_mock()
            _update_locked_funds_from_last_orders_trades_mock.reset_mock()
            sleep_mock.reset_mock()
            # 2nd cycle trigger
            await asyncio_tools.wait_asyncio_next_cycle()
            # _initialize_locked_funds_mock is only called once
            _initialize_locked_funds_mock.assert_not_called()
            _trigger_mock.assert_called_once()
            _update_locked_funds_from_last_orders_trades_mock.assert_called_once_with([])
            sleep_mock.assert_called_once()
            _initialize_locked_funds_mock.reset_mock()
            _trigger_mock.reset_mock()
            _update_locked_funds_from_last_orders_trades_mock.reset_mock()
            sleep_mock.reset_mock()
            # now stop
            scheduled_volume.stop()
            await asyncio_tools.wait_asyncio_next_cycle()
            # stopped: didn't call anything
            _initialize_locked_funds_mock.assert_not_called()
            _trigger_mock.assert_not_called()
            _update_locked_funds_from_last_orders_trades_mock.assert_not_called()
            sleep_mock.assert_not_called()
            assert schedule_loop_task.done()


@pytest.mark.asyncio
async def test_trigger_no_current_price(scheduled_volume):
    # no current price
    for current_price in (None, decimal.Decimal("NaN")):
        with mock.patch.object(
            personal_data, 'get_pre_order_data', mock.AsyncMock(return_value=(None, None, None, current_price, {}))
        ) as get_pre_order_data_mock, mock.patch.object(
            scheduled_volume, '_get_next_orders', mock.Mock(return_value=[])
        ) as _get_next_orders_mock, mock.patch.object(
            scheduled_volume, '_call_on_missing_funds_if_needed', mock.AsyncMock(return_value=True)
        ) as _call_on_missing_funds_if_needed_mock:
            scheduled_volume.exchange_manager.trader.create_order = mock.AsyncMock()
            assert await scheduled_volume._trigger() == []
            get_pre_order_data_mock.assert_called_once()
            _call_on_missing_funds_if_needed_mock.assert_not_called()
            _get_next_orders_mock.assert_not_called()
            scheduled_volume.exchange_manager.trader.create_order.assert_not_called()
            assert scheduled_volume._last_order_side == trading_enums.TradeOrderSide.SELL
            assert scheduled_volume._healthy is False


@pytest.mark.asyncio
async def test_trigger_no_created_order(scheduled_volume):
    current_price = decimal.Decimal("25000.1")
    with mock.patch.object(
        personal_data, 'get_pre_order_data', mock.AsyncMock(return_value=(None, None, None, current_price, {}))
    ) as get_pre_order_data_mock, mock.patch.object(
        scheduled_volume, '_get_next_orders', mock.Mock(return_value=[])
    ) as _get_next_orders_mock, mock.patch.object(
        scheduled_volume, '_call_on_missing_funds_if_needed', mock.AsyncMock(return_value=True)
    ) as _call_on_missing_funds_if_needed_mock:
        scheduled_volume.exchange_manager.trader.create_order = mock.AsyncMock()
        assert await scheduled_volume._trigger() == []
        _call_on_missing_funds_if_needed_mock.assert_called_once()
        get_pre_order_data_mock.assert_called_once()
        _get_next_orders_mock.assert_called_once()
        scheduled_volume.exchange_manager.trader.create_order.assert_not_called()
        assert scheduled_volume._last_order_side == trading_enums.TradeOrderSide.SELL
        assert scheduled_volume._healthy is False


@pytest.mark.asyncio
async def test_trigger_created_order_with_error_returning_none(scheduled_volume):
    current_price = decimal.Decimal("25000.1")
    buy_1 = personal_data.BuyLimitOrder(scheduled_volume.exchange_manager.trader)
    buy_1.update(
        order_type=trading_enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.07"),
        price=decimal.Decimal("20000")
    )
    with mock.patch.object(
        personal_data, 'get_pre_order_data', mock.AsyncMock(return_value=(None, None, None, current_price, {}))
    ) as get_pre_order_data_mock, mock.patch.object(
        scheduled_volume, '_get_next_orders', mock.Mock(return_value=[buy_1])
    ) as _get_next_orders_mock, mock.patch.object(
        scheduled_volume, '_call_on_missing_funds_if_needed', mock.AsyncMock(return_value=True)
    ) as _call_on_missing_funds_if_needed_mock:
        scheduled_volume.exchange_manager.trader.create_order = mock.AsyncMock(return_value=None)
        assert await scheduled_volume._trigger() == []
        _call_on_missing_funds_if_needed_mock.assert_not_called()
        get_pre_order_data_mock.assert_called_once()
        _get_next_orders_mock.assert_called_once()
        scheduled_volume.exchange_manager.trader.create_order.assert_called_once()
        assert scheduled_volume._last_order_side == trading_enums.TradeOrderSide.SELL
        assert scheduled_volume._healthy is False


@pytest.mark.asyncio
async def test_trigger_successful_order_creation(scheduled_volume):
    current_price = decimal.Decimal("25000.1")
    buy_1 = personal_data.BuyLimitOrder(scheduled_volume.exchange_manager.trader)
    buy_1.update(
        order_type=trading_enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.07"),
        price=decimal.Decimal("20000")
    )
    buy_2 = personal_data.BuyLimitOrder(scheduled_volume.exchange_manager.trader)
    buy_2.update(
        order_type=trading_enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("5000"),
        quantity=decimal.Decimal("0.07"),
        price=decimal.Decimal("2000")
    )

    with mock.patch.object(
        personal_data, 'get_pre_order_data', mock.AsyncMock(return_value=(None, None, None, current_price, {}))
    ) as get_pre_order_data_mock, mock.patch.object(
        scheduled_volume, '_get_next_orders', mock.Mock(return_value=[buy_1, buy_2])
    ) as _get_next_orders_mock, mock.patch.object(
        scheduled_volume, '_call_on_missing_funds_if_needed', mock.AsyncMock(return_value=True)
    ) as _call_on_missing_funds_if_needed_mock:
        scheduled_volume.exchange_manager.trader.create_order = mock.AsyncMock(return_value=buy_2)
        assert await scheduled_volume._trigger() == [buy_2, buy_2]
        get_pre_order_data_mock.assert_called_once()
        _call_on_missing_funds_if_needed_mock.assert_not_called()
        _get_next_orders_mock.assert_called_once()
        assert scheduled_volume.exchange_manager.trader.create_order.call_count == 2
        assert scheduled_volume.exchange_manager.trader.create_order.mock_calls[0].args == (buy_1,)
        assert scheduled_volume.exchange_manager.trader.create_order.mock_calls[1].args == (buy_2,)
        assert scheduled_volume._last_order_side == trading_enums.TradeOrderSide.BUY
        assert scheduled_volume._healthy is True


@pytest.mark.asyncio
async def test_call_on_missing_funds_if_needed(scheduled_volume):
    assert scheduled_volume._last_on_missing_funds_callback_call_time == 0
    scheduled_volume._on_missing_funds_callback.assert_not_called()
    assert await scheduled_volume._call_on_missing_funds_if_needed() is True
    assert scheduled_volume._last_on_missing_funds_callback_call_time > 0
    scheduled_volume._on_missing_funds_callback.assert_called_once()
    scheduled_volume._on_missing_funds_callback.reset_mock()
    # immediately call again: need some time
    assert await scheduled_volume._call_on_missing_funds_if_needed() is False
    scheduled_volume._on_missing_funds_callback.assert_not_called()
    assert await scheduled_volume._call_on_missing_funds_if_needed() is False
    scheduled_volume._on_missing_funds_callback.assert_not_called()
    with mock.patch.object(
        time, "time",
        mock.Mock(return_value=time.time()+scheduled_volume_import._ON_MISSING_FUNDS_MAX_CHECK_INTERVAL+1)
    ) as time_mock:
        assert await scheduled_volume._call_on_missing_funds_if_needed() is True
        time_mock.assert_called_once()
        time_mock.reset_mock()
        scheduled_volume._on_missing_funds_callback.assert_called_once()
        scheduled_volume._on_missing_funds_callback.reset_mock()
        assert await scheduled_volume._call_on_missing_funds_if_needed() is False
        time_mock.assert_called_once()
        scheduled_volume._on_missing_funds_callback.assert_not_called()


@pytest.mark.asyncio
async def test_update_locked_funds_from_last_orders_trades_with_trade(scheduled_volume):
    buy_1 = personal_data.BuyLimitOrder(scheduled_volume.exchange_manager.trader)
    buy_1.update(
        order_type=trading_enums.TraderOrderType.BUY_LIMIT,
        symbol="BTC/USDT",
        current_price=decimal.Decimal("25000"),
        quantity=decimal.Decimal("0.07"),
        quantity_filled=decimal.Decimal("0.07"),
        price=decimal.Decimal("20000"),
        fee={
            trading_enums.FeePropertyColumns.CURRENCY.value: "BTC",
            trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.002"),
        }
    )
    trade_1 = personal_data.create_trade_from_order(buy_1)
    trade_1.fee = {
        trading_enums.FeePropertyColumns.CURRENCY.value: "BTC",
        trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.0022"),
    }

    trades_manager = mock.Mock()
    scheduled_volume.exchange_manager.exchange_personal_data.trades_manager = trades_manager

    # Mock trading_api.get_portfolio_currency
    mock_portfolio = mock.Mock()
    mock_portfolio.available = decimal.Decimal("2.1")
    with mock.patch.object(
        octobot_trading.api, 'get_portfolio_currency', mock.Mock(return_value=mock_portfolio)
    ), mock.patch.object(
        scheduled_volume_import, 'get_global_locked_funds', mock.Mock(return_value=decimal.Decimal("0"))
    ) as get_global_locked_funds_mock, mock.patch.object(
        scheduled_volume, '_update_locked_funds', mock.Mock(return_value=decimal.Decimal("0"))
    ) as _update_locked_funds_mock:
        # no order
        scheduled_volume._update_locked_funds_from_last_orders_trades([])
        get_global_locked_funds_mock.assert_not_called()
        _update_locked_funds_mock.assert_not_called()
        trades_manager.get_trades.assert_not_called()

        # with order without trade: take fees from trade
        trades_manager.get_trades.return_value = [trade_1]
        scheduled_volume._update_locked_funds_from_last_orders_trades([buy_1])
        trades_manager.get_trades.assert_called_once_with(exchange_order_id=buy_1.exchange_order_id)
        assert get_global_locked_funds_mock.call_count == 2
        _update_locked_funds_mock.assert_called_once_with(
            decimal.Decimal("0.07") - decimal.Decimal("0.0022"), # trade fee
            trading_constants.ZERO
        )
        get_global_locked_funds_mock.reset_mock()
        _update_locked_funds_mock.reset_mock()
        trades_manager.get_trades.reset_mock()

        # with order without trade: take fees from order
        trades_manager.get_trades.return_value = []
        scheduled_volume._update_locked_funds_from_last_orders_trades([buy_1])
        trades_manager.get_trades.assert_called_once_with(exchange_order_id=buy_1.exchange_order_id)
        assert get_global_locked_funds_mock.call_count == 2
        _update_locked_funds_mock.assert_called_once_with(
            decimal.Decimal("0.07") - decimal.Decimal("0.002"), # order fee
            trading_constants.ZERO
        )
        get_global_locked_funds_mock.reset_mock()
        _update_locked_funds_mock.reset_mock()
        trades_manager.get_trades.reset_mock()

        # with 2 orders: only 1st with trade
        sell_1 = personal_data.SellLimitOrder(scheduled_volume.exchange_manager.trader)
        sell_1.update(
            exchange_order_id="sell_1",
            order_type=trading_enums.TraderOrderType.SELL_LIMIT,
            symbol="BTC/USDT",
            current_price=decimal.Decimal("25000"),
            quantity=decimal.Decimal("0.05"),
            quantity_filled=decimal.Decimal("0.05"),
            price=decimal.Decimal("35000")
        )
        def _get_trades(exchange_order_id):
            if exchange_order_id == buy_1.exchange_order_id:
                return [trade_1]
            return []

        trades_manager.get_trades = mock.Mock(side_effect=_get_trades)
        scheduled_volume._update_locked_funds_from_last_orders_trades([buy_1, sell_1])
        assert trades_manager.get_trades.call_count == 2
        assert trades_manager.get_trades.mock_calls[0].kwargs=={"exchange_order_id": buy_1.exchange_order_id}
        assert trades_manager.get_trades.mock_calls[0].kwargs=={"exchange_order_id": buy_1.exchange_order_id}
        assert get_global_locked_funds_mock.call_count == 2
        _update_locked_funds_mock.assert_called_once_with(
            decimal.Decimal("0.07") - decimal.Decimal("0.05") - decimal.Decimal("0.0022"), # trade fee
            decimal.Decimal("2.1")    # 350 maxed at 2.1 since only 2.1 is available (from mock)
        )
        get_global_locked_funds_mock.reset_mock()
        _update_locked_funds_mock.reset_mock()
        trades_manager.get_trades.reset_mock()


def test_get_next_orders(scheduled_volume):
    with mock.patch.object(
        scheduled_volume, "_get_next_sided_orders", mock.Mock(return_value=[])
    ) as _get_next_sided_orders_mock:
        current_price = decimal.Decimal("1.0")
        symbol_market = mock.Mock()
        assert scheduled_volume._get_next_orders(current_price, symbol_market) == []
        # try both sides as _get_next_sided_orders returns no order
        assert _get_next_sided_orders_mock.call_count == 2
        assert _get_next_sided_orders_mock.mock_calls[0].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.BUY
        )
        assert _get_next_sided_orders_mock.mock_calls[1].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.SELL
        )
        # last order is a buy
        _get_next_sided_orders_mock.reset_mock()
        scheduled_volume._last_order_side = trading_enums.TradeOrderSide.SELL
        assert scheduled_volume._get_next_orders(current_price, symbol_market) == []
        # try both sides as _get_next_sided_orders returns no order
        assert _get_next_sided_orders_mock.call_count == 2
        assert _get_next_sided_orders_mock.mock_calls[0].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.BUY
        )
        assert _get_next_sided_orders_mock.mock_calls[1].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.SELL
        )
        # last order is a sell
        _get_next_sided_orders_mock.reset_mock()
        scheduled_volume._last_order_side = trading_enums.TradeOrderSide.BUY
        assert scheduled_volume._get_next_orders(current_price, symbol_market) == []
        # try both sides as _get_next_sided_orders returns no order
        assert _get_next_sided_orders_mock.call_count == 2
        assert _get_next_sided_orders_mock.mock_calls[0].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.SELL
        )
        assert _get_next_sided_orders_mock.mock_calls[1].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.BUY
        )
    order = mock.Mock()
    with mock.patch.object(
        scheduled_volume, "_get_next_sided_orders", mock.Mock(return_value=[order])
    ) as _get_next_sided_orders_mock:
        scheduled_volume._last_order_side = trading_enums.TradeOrderSide.SELL
        current_price = decimal.Decimal("1.01")
        symbol_market = mock.Mock()
        assert scheduled_volume._get_next_orders(current_price, symbol_market) == [order]
        # try both sides as _get_next_sided_orders returns no order
        assert _get_next_sided_orders_mock.call_count == 1
        assert _get_next_sided_orders_mock.mock_calls[0].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.BUY
        )
        _get_next_sided_orders_mock.reset_mock()

        scheduled_volume._last_order_side = trading_enums.TradeOrderSide.BUY
        assert scheduled_volume._get_next_orders(current_price, symbol_market) == [order]
        # try both sides as _get_next_sided_orders returns no order
        assert _get_next_sided_orders_mock.call_count == 1
        assert _get_next_sided_orders_mock.mock_calls[0].args == (
            current_price, symbol_market, trading_enums.TradeOrderSide.SELL
        )


def test_get_next_sided_orders(scheduled_volume):
    current_price = decimal.Decimal("50000.1")
    symbol_market = {"limits": {"cost": {"min": 10}}}
    scheduled_volume._get_locked_base_and_quote = mock.Mock()

    mock_portfolio = mock.Mock()
    mock_portfolio.available = decimal.Decimal("1000")  # Available quote currency for buying

    with mock.patch.object(octobot_trading.api, 'get_portfolio_currency', mock.Mock(return_value=mock_portfolio)), \
            mock.patch.object(random, 'uniform', mock.Mock(return_value=150)), \
            mock.patch.object(personal_data, 'decimal_check_and_adapt_order_details_if_necessary') as mock_adapt:
        mock_adapt.return_value = [(decimal.Decimal("0.001"), current_price)]
        scheduled_volume._get_locked_base_and_quote.return_value = (
            decimal.Decimal("1"),  # locked base
            decimal.Decimal("2000")  # locked quote
        )

        result = scheduled_volume._get_next_sided_orders(current_price, symbol_market, trading_enums.TradeOrderSide.BUY)

        assert len(result) == 1
        created_order = result[0]
        assert isinstance(created_order, personal_data.BuyMarketOrder)
        assert created_order.total_cost == decimal.Decimal("50.0001")
        mock_adapt.assert_called_once()
        mock_adapt.reset_mock()

        result = scheduled_volume._get_next_sided_orders(current_price, symbol_market, trading_enums.TradeOrderSide.SELL)

        assert len(result) == 1
        created_order = result[0]
        assert isinstance(created_order, personal_data.SellMarketOrder)
        assert created_order.total_cost == decimal.Decimal("50.0001")
        mock_adapt.assert_called_once()
        mock_adapt.reset_mock()

def test_get_next_sided_orders_minimum_cost_adjustment(scheduled_volume):

    current_price = decimal.Decimal("50000.2222")
    symbol_market = {"limits": {"cost": {"min": 200}}}  # Higher minimum cost
    side = trading_enums.TradeOrderSide.BUY

    mock_portfolio = mock.Mock()
    mock_portfolio.available = decimal.Decimal("1000")  # Available quote currency for buying
    scheduled_volume._get_locked_base_and_quote = mock.Mock()

    with mock.patch.object(octobot_trading.api, 'get_portfolio_currency', mock.Mock(return_value=mock_portfolio)), \
            mock.patch.object(random, 'uniform', mock.Mock(return_value=150)), \
            mock.patch.object(personal_data, 'decimal_check_and_adapt_order_details_if_necessary') as mock_adapt:
        mock_adapt.return_value = [(decimal.Decimal("0.005"), current_price)]
        scheduled_volume._get_locked_base_and_quote.return_value = (
            decimal.Decimal("1"),
            decimal.Decimal("2000")
        )

        result = scheduled_volume._get_next_sided_orders(current_price, symbol_market, side)

        assert len(result) == 1
        # Verify that the order amount is adjusted to meet minimum cost requirement
        mock_adapt.assert_called_once()
        args = mock_adapt.call_args[0]
        assert args[0] >= decimal.Decimal("200") / current_price  # Minimum cost requirement met
        assert result[0].total_cost == decimal.Decimal("250.0011110")   # higher than 150 (would be the cost without this min)

def test_get_next_sided_orders_insufficient_funds(scheduled_volume):
    current_price = decimal.Decimal("50000")
    symbol_market = {"limits": {"cost": {"min": 200}}}  # Higher minimum cost
    side = trading_enums.TradeOrderSide.BUY

    mock_portfolio = mock.Mock()
    mock_portfolio.available = decimal.Decimal("5")  # Very low available funds
    scheduled_volume._get_locked_base_and_quote = mock.Mock()

    with mock.patch.object(octobot_trading.api, 'get_portfolio_currency', mock.Mock(return_value=mock_portfolio)), \
            mock.patch.object(random, 'uniform', mock.Mock(return_value=500)), \
            mock.patch.object(personal_data, 'decimal_check_and_adapt_order_details_if_necessary') as mock_adapt:
        mock_adapt.return_value = []
        scheduled_volume._get_locked_base_and_quote.return_value = (
            decimal.Decimal("1"),
            decimal.Decimal("2000")
        )
        # Act
        result = scheduled_volume._get_next_sided_orders(current_price, symbol_market, side)

        # Assert
        assert result == []


def test_get_next_sided_orders_decimal_error(scheduled_volume):
    current_price = decimal.Decimal("0")  # Will cause division by zero
    symbol_market = {"limits": {"cost": {"min": 200}}}
    side = trading_enums.TradeOrderSide.BUY

    mock_portfolio = mock.Mock()
    mock_portfolio.available = decimal.Decimal("5")
    scheduled_volume._get_locked_base_and_quote = mock.Mock()
    scheduled_volume.logger = mock.Mock()

    with mock.patch.object(octobot_trading.api, 'get_portfolio_currency', mock.Mock(return_value=mock_portfolio)), \
            mock.patch.object(random, 'uniform', mock.Mock(return_value=500)), \
            mock.patch.object(personal_data, 'decimal_check_and_adapt_order_details_if_necessary') as mock_adapt:
        scheduled_volume._get_locked_base_and_quote.return_value = (
            decimal.Decimal("1"),
            decimal.Decimal("2000")
        )

        with pytest.raises(ValueError):
            scheduled_volume._get_next_sided_orders(current_price, symbol_market, side)


def test_get_next_sided_orders_locked_funds_limit(scheduled_volume):
    current_price = decimal.Decimal("50000")
    symbol_market = {"limits": {"cost": {"min": 10}}}

    mock_portfolio = mock.Mock()
    mock_portfolio.available = decimal.Decimal("20")
    scheduled_volume._get_locked_base_and_quote = mock.Mock()
    scheduled_volume.logger = mock.Mock()

    with mock.patch.object(octobot_trading.api, 'get_portfolio_currency', mock.Mock(return_value=mock_portfolio)), \
            mock.patch.object(random, 'uniform', mock.Mock(return_value=500)), \
            mock.patch.object(personal_data, 'decimal_check_and_adapt_order_details_if_necessary') as mock_adapt:
        mock_adapt.return_value = [(decimal.Decimal("0.1"), current_price)]
        # Set low locked funds to limit order size
        scheduled_volume._get_locked_base_and_quote.return_value = (
            decimal.Decimal("0.005"),  # small locked base
            decimal.Decimal("250")  # small locked quote
        )

        result = scheduled_volume._get_next_sided_orders(current_price, symbol_market, trading_enums.TradeOrderSide.BUY)

        assert len(result) == 1
        mock_adapt.assert_called_once()
        # Verify that the order amount is limited by available funds
        args = mock_adapt.call_args[0]
        assert args[0] == decimal.Decimal("20") / current_price
        mock_adapt.reset_mock()

        result = scheduled_volume._get_next_sided_orders(current_price, symbol_market, trading_enums.TradeOrderSide.SELL)

        assert len(result) == 1
        mock_adapt.assert_called_once()
        # Verify that the order amount is limited by available funds
        args = mock_adapt.call_args[0]
        assert args[0] == decimal.Decimal("0.005")
