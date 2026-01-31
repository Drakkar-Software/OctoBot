#  Drakkar-Software OctoBot-Trading
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
import decimal
import os

import mock
import pytest
from mock import patch, Mock, AsyncMock
import octobot_commons.constants as commons_constants
import octobot_trading.personal_data as personal_data
import octobot_trading.errors as errors
import octobot_trading.enums as enums
from octobot_trading.personal_data.orders import BuyMarketOrder, BuyLimitOrder
import octobot_trading.personal_data.portfolios.update_events as update_events

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

# All test coroutines will be treated as marked.
from tests.personal_data import DEFAULT_MARKET_QUANTITY
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity

pytestmark = pytest.mark.asyncio


async def test_handle_balance_update(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    if os.getenv('CYTHON_IGNORE'):
        return

    with patch.object(portfolio_manager.portfolio, 'update_portfolio_from_balance',
                      new=Mock()) as update_portfolio_from_balance_mock:
        update_portfolio_from_balance_mock.assert_not_called()

        portfolio_manager.handle_balance_update(None)
        update_portfolio_from_balance_mock.assert_not_called()

        with mock.patch.object(trader, 'can_trade_if_not_paused', return_value=False) as can_trade_if_not_paused_mock:
            portfolio_manager.handle_balance_update({})
            update_portfolio_from_balance_mock.assert_not_called()
            can_trade_if_not_paused_mock.assert_called_once()

        with mock.patch.object(trader, 'can_trade_if_not_paused', return_value=True) as can_trade_if_not_paused_mock:
            portfolio_manager.handle_balance_update({})
            update_portfolio_from_balance_mock.assert_called_once()
            can_trade_if_not_paused_mock.assert_called_once()


async def test_handle_balance_update_from_order(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    trader.simulate = False
    order = BuyMarketOrder(trader)
    # Set order as active so it goes through the real trader path when require_exchange_update=True
    with patch.object(order, 'is_active', True), \
         patch.object(portfolio_manager, '_refresh_real_trader_portfolio_and_init_event_checker_if_needed',
                      new=AsyncMock(return_value=(True, None))) as _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock, \
         patch.object(portfolio_manager, '_refresh_simulated_trader_portfolio_from_order',
                     new=Mock(return_value=True)) as _refresh_simulated_trader_portfolio_from_order_mock:
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
        result = await portfolio_manager.handle_balance_update_from_order(order, True, False)
        assert result == (True, None)
        # Verify the call was made with FilledOrderUpdateEvent and expect_filled_order_update=False
        assert _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_count == 1
        call_args = _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_args
        assert isinstance(call_args[0][0], update_events.FilledOrderUpdateEvent)
        assert call_args[0][1] is False
        _refresh_simulated_trader_portfolio_from_order_mock.assert_not_called()
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.reset_mock()
        
        result = await portfolio_manager.handle_balance_update_from_order(order, True, True)
        assert result == (True, None)
        assert _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_count == 1
        call_args = _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_args
        assert isinstance(call_args[0][0], update_events.FilledOrderUpdateEvent)
        assert call_args[0][1] is True
        _refresh_simulated_trader_portfolio_from_order_mock.assert_not_called()
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.reset_mock()
        
        with portfolio_manager.disabled_portfolio_update_from_order():
            result = await portfolio_manager.handle_balance_update_from_order(order, False, False)
            assert result == (True, None)
            _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
            _refresh_simulated_trader_portfolio_from_order_mock.assert_called_once()
            _refresh_simulated_trader_portfolio_from_order_mock.reset_mock()
            
            result = await portfolio_manager.handle_balance_update_from_order(order, True, False)
            assert result == (True, None)
            _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
            _refresh_simulated_trader_portfolio_from_order_mock.assert_called_once()
            _refresh_simulated_trader_portfolio_from_order_mock.reset_mock()
        
        result = await portfolio_manager.handle_balance_update_from_order(order, False, False)
        assert result == (True, None)
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
        _refresh_simulated_trader_portfolio_from_order_mock.assert_called_once()

    trader.simulate = True
    with patch.object(portfolio_manager, '_refresh_simulated_trader_portfolio_from_order',
                      new=Mock(return_value=True)) as _refresh_simulated_trader_portfolio_from_order_mock:
        _refresh_simulated_trader_portfolio_from_order_mock.assert_not_called()
        result = await portfolio_manager.handle_balance_update_from_order(order, True, False)
        assert result == (True, None)
        _refresh_simulated_trader_portfolio_from_order_mock.assert_called_once()
        _refresh_simulated_trader_portfolio_from_order_mock.reset_mock()
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
        
        with portfolio_manager.disabled_portfolio_update_from_order():
            result = await portfolio_manager.handle_balance_update_from_order(order, True, False)
            assert result == (True, None)
            _refresh_simulated_trader_portfolio_from_order_mock.assert_called_once()
            _refresh_simulated_trader_portfolio_from_order_mock.reset_mock()
            _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
            
            result = await portfolio_manager.handle_balance_update_from_order(order, False, False)
            assert result == (True, None)
            _refresh_simulated_trader_portfolio_from_order_mock.assert_called_once()
            _refresh_simulated_trader_portfolio_from_order_mock.reset_mock()
            _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
        
        # ensure no side effect with require_exchange_update param
        result = await portfolio_manager.handle_balance_update_from_order(order, False, False)
        assert result == (True, None)
        _refresh_simulated_trader_portfolio_from_order_mock.assert_called_once()
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()

    with mock.patch.object(trader, 'can_trade_if_not_paused', return_value=False) as can_trade_if_not_paused_mock:
        trader.simulate = False
        result = await portfolio_manager.handle_balance_update_from_order(order, True, False)
        assert result == (False, None)
        result = await portfolio_manager.handle_balance_update_from_order(order, False, False)
        assert result == (False, None)
        assert can_trade_if_not_paused_mock.call_count == 2
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()


async def test_handle_balance_update_from_withdrawal(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    amount = decimal.Decimal("10")
    currency = "USDT"
    transaction = {
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount,
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: currency
    }
    
    with patch.object(
        portfolio_manager, '_refresh_real_trader_portfolio_and_init_event_checker_if_needed', 
        mock.AsyncMock(return_value=(True, None))
    ) as _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock:
        # Test when trader is disabled in config
        trader.is_enabled = False
        trader.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_ENABLED_OPTION] = False
        initial_available = portfolio_manager.portfolio.get_currency_portfolio(currency).available
        initial_total = portfolio_manager.portfolio.get_currency_portfolio(currency).total
        result = await portfolio_manager.handle_balance_update_from_withdrawal(transaction, False)
        assert result == (False, None)
        # Portfolio should not be updated
        assert portfolio_manager.portfolio.get_currency_portfolio(currency).available == initial_available
        assert portfolio_manager.portfolio.get_currency_portfolio(currency).total == initial_total
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
        
        # Test when enable_portfolio_exchange_sync is False
        trader.is_enabled = True
        trader.config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_ENABLED_OPTION] = True
        portfolio_manager.enable_portfolio_exchange_sync = False
        trader.simulate = False
        initial_available = portfolio_manager.portfolio.get_currency_portfolio(currency).available
        initial_total = portfolio_manager.portfolio.get_currency_portfolio(currency).total
        result = await portfolio_manager.handle_balance_update_from_withdrawal(transaction, False)
        assert result == (True, None)
        # Portfolio should be updated directly
        assert portfolio_manager.portfolio.get_currency_portfolio(currency).available == initial_available - amount
        assert portfolio_manager.portfolio.get_currency_portfolio(currency).total == initial_total - amount
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
        
        # Test when simulating
        portfolio_manager.enable_portfolio_exchange_sync = True
        trader.simulate = True
        initial_available = portfolio_manager.portfolio.get_currency_portfolio(currency).available
        initial_total = portfolio_manager.portfolio.get_currency_portfolio(currency).total
        result = await portfolio_manager.handle_balance_update_from_withdrawal(transaction, False)
        assert result == (True, None)
        # Portfolio should be updated directly
        assert portfolio_manager.portfolio.get_currency_portfolio(currency).available == initial_available - amount
        assert portfolio_manager.portfolio.get_currency_portfolio(currency).total == initial_total - amount
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.assert_not_called()
        
        # Test when real trader with exchange sync enabled
        # This will attempt to refresh from exchange
        trader.simulate = False
        result = await portfolio_manager.handle_balance_update_from_withdrawal(transaction, False)
        assert result == (True, None)
        # Verify the call was made with TransactionUpdateEvent and expect_withdrawal_update=False
        assert _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_count == 1
        call_args = _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_args
        assert isinstance(call_args[0][0], update_events.TransactionUpdateEvent)
        assert call_args[0][1] is False
        _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.reset_mock()
        
        # Test with expect_withdrawal_update=True
        result = await portfolio_manager.handle_balance_update_from_withdrawal(transaction, True)
        assert result == (True, None)
        assert _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_count == 1
        call_args = _refresh_real_trader_portfolio_and_init_event_checker_if_needed_mock.call_args
        assert isinstance(call_args[0][0], update_events.TransactionUpdateEvent)
        assert call_args[0][1] is True


async def test_refresh_real_trader_portfolio_and_init_event_checker_if_needed(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    trader.simulate = False
    order = BuyMarketOrder(trader)
    order.update("BTC/USDT", quantity=decimal.Decimal(10), price=decimal.Decimal(100))
    event = update_events.FilledOrderUpdateEvent(order)
    
    # Clear any existing pending events
    portfolio_manager.pending_portfolio_update_events = []
    
    with patch.object(portfolio_manager, '_refresh_real_trader_portfolio',
                      new=AsyncMock(return_value=True)) as _refresh_real_trader_portfolio_mock, \
         patch.object(portfolio_manager, 'start_expected_portfolio_update_checker',
                      new=AsyncMock()) as start_expected_portfolio_update_checker_mock:
        
        # Test when update_expected=False
        result = await portfolio_manager._refresh_real_trader_portfolio_and_init_event_checker_if_needed(event, False)
        assert result == (True, None)
        assert len(portfolio_manager.pending_portfolio_update_events) == 1
        assert portfolio_manager.pending_portfolio_update_events[0] == event
        _refresh_real_trader_portfolio_mock.assert_called_once()
        start_expected_portfolio_update_checker_mock.assert_not_called()
        
        # Reset mocks and clear pending events
        _refresh_real_trader_portfolio_mock.reset_mock()
        portfolio_manager.pending_portfolio_update_events = []
        
        # Test when update_expected=True and event is not set
        event2 = update_events.FilledOrderUpdateEvent(order)
        assert not event2.is_set()
        result = await portfolio_manager._refresh_real_trader_portfolio_and_init_event_checker_if_needed(event2, True)
        assert result == (True, event2)
        assert len(portfolio_manager.pending_portfolio_update_events) == 1
        assert portfolio_manager.pending_portfolio_update_events[0] == event2
        _refresh_real_trader_portfolio_mock.assert_called_once()
        start_expected_portfolio_update_checker_mock.assert_called_once()
        
        # Reset mocks and clear pending events
        _refresh_real_trader_portfolio_mock.reset_mock()
        start_expected_portfolio_update_checker_mock.reset_mock()
        portfolio_manager.pending_portfolio_update_events = []
        
        # Test when update_expected=True and event is already set
        event3 = update_events.FilledOrderUpdateEvent(order)
        event3.set()  # Set the event
        assert event3.is_set()
        result = await portfolio_manager._refresh_real_trader_portfolio_and_init_event_checker_if_needed(event3, True)
        assert result == (True, event3)
        assert len(portfolio_manager.pending_portfolio_update_events) == 1
        assert portfolio_manager.pending_portfolio_update_events[0] == event3
        _refresh_real_trader_portfolio_mock.assert_called_once()
        start_expected_portfolio_update_checker_mock.assert_not_called()
        
        # Test when _refresh_real_trader_portfolio returns False
        _refresh_real_trader_portfolio_mock.reset_mock()
        portfolio_manager.pending_portfolio_update_events = []
        _refresh_real_trader_portfolio_mock.return_value = False
        event4 = update_events.FilledOrderUpdateEvent(order)
        result = await portfolio_manager._refresh_real_trader_portfolio_and_init_event_checker_if_needed(event4, False)
        assert result == (False, None)
        assert len(portfolio_manager.pending_portfolio_update_events) == 1
        assert portfolio_manager.pending_portfolio_update_events[0] == event4
        _refresh_real_trader_portfolio_mock.assert_called_once()
        start_expected_portfolio_update_checker_mock.assert_not_called()


async def test_resolve_pending_portfolio_update_events_if_any(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    trader.simulate = False
    
    # Create a local implementation of PortfolioUpdateEvent with controllable is_resolved behavior
    class TestPortfolioUpdateEvent(update_events.PortfolioUpdateEvent):
        def __init__(self, is_resolved_value: bool):
            super().__init__()
            self._is_resolved_value = is_resolved_value
            self._set_called = False
        
        def is_resolved(self, updated_portfolio):
            return self._is_resolved_value
        
        def set(self):
            super().set()
            self._set_called = True
    
    with patch.object(portfolio_manager, 'stop_expected_portfolio_update_checker',
                      new=AsyncMock()) as stop_expected_portfolio_update_checker_mock:
        
        # Test when there are no pending events
        portfolio_manager.pending_portfolio_update_events = []
        assert portfolio_manager.has_pending_portfolio_update_events() is False
        await portfolio_manager.resolve_pending_portfolio_update_events_if_any()
        assert len(portfolio_manager.pending_portfolio_update_events) == 0
        stop_expected_portfolio_update_checker_mock.assert_called_once()
        stop_expected_portfolio_update_checker_mock.reset_mock()
        
        # Test when all events are resolved
        resolved_event1 = TestPortfolioUpdateEvent(is_resolved_value=True)
        resolved_event2 = TestPortfolioUpdateEvent(is_resolved_value=True)
        portfolio_manager.pending_portfolio_update_events = [resolved_event1, resolved_event2]
        assert portfolio_manager.has_pending_portfolio_update_events() is True
        assert not resolved_event1.is_set()
        assert not resolved_event2.is_set()
        await portfolio_manager.resolve_pending_portfolio_update_events_if_any()
        assert len(portfolio_manager.pending_portfolio_update_events) == 0
        assert resolved_event1.is_set()
        assert resolved_event2.is_set()
        assert resolved_event1._set_called
        assert resolved_event2._set_called
        stop_expected_portfolio_update_checker_mock.assert_called_once()
        stop_expected_portfolio_update_checker_mock.reset_mock()
        
        # Test when all events are unresolved
        unresolved_event1 = TestPortfolioUpdateEvent(is_resolved_value=False)
        unresolved_event2 = TestPortfolioUpdateEvent(is_resolved_value=False)
        portfolio_manager.pending_portfolio_update_events = [unresolved_event1, unresolved_event2]
        assert portfolio_manager.has_pending_portfolio_update_events() is True
        await portfolio_manager.resolve_pending_portfolio_update_events_if_any()
        assert len(portfolio_manager.pending_portfolio_update_events) == 2
        assert unresolved_event1 in portfolio_manager.pending_portfolio_update_events
        assert unresolved_event2 in portfolio_manager.pending_portfolio_update_events
        assert not unresolved_event1.is_set()
        assert not unresolved_event2.is_set()
        assert not unresolved_event1._set_called
        assert not unresolved_event2._set_called
        stop_expected_portfolio_update_checker_mock.assert_not_called()
        stop_expected_portfolio_update_checker_mock.reset_mock()
        
        # Test when there are mixed resolved and unresolved events
        resolved_event3 = TestPortfolioUpdateEvent(is_resolved_value=True)
        resolved_event4 = TestPortfolioUpdateEvent(is_resolved_value=True)
        unresolved_event3 = TestPortfolioUpdateEvent(is_resolved_value=False)
        unresolved_event4 = TestPortfolioUpdateEvent(is_resolved_value=False)
        
        portfolio_manager.pending_portfolio_update_events = [
            resolved_event3, unresolved_event3, resolved_event4, unresolved_event4
        ]
        assert portfolio_manager.has_pending_portfolio_update_events() is True
        await portfolio_manager.resolve_pending_portfolio_update_events_if_any()
        assert len(portfolio_manager.pending_portfolio_update_events) == 2
        assert unresolved_event3 in portfolio_manager.pending_portfolio_update_events
        assert unresolved_event4 in portfolio_manager.pending_portfolio_update_events
        assert resolved_event3 not in portfolio_manager.pending_portfolio_update_events
        assert resolved_event4 not in portfolio_manager.pending_portfolio_update_events
        assert resolved_event3.is_set()
        assert resolved_event4.is_set()
        assert resolved_event3._set_called
        assert resolved_event4._set_called
        assert not unresolved_event3.is_set()
        assert not unresolved_event4.is_set()
        assert not unresolved_event3._set_called
        assert not unresolved_event4._set_called
        stop_expected_portfolio_update_checker_mock.assert_not_called()


async def test_handle_balance_update_from_deposit(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    amount = decimal.Decimal("10")
    currency = "USDT"
    
    # Test when simulating - should update portfolio
    trader.simulate = True
    initial_available = portfolio_manager.portfolio.get_currency_portfolio(currency).available
    initial_total = portfolio_manager.portfolio.get_currency_portfolio(currency).total
    await portfolio_manager.handle_balance_update_from_deposit(amount, currency)
    # Portfolio should be updated with deposit amount added
    assert portfolio_manager.portfolio.get_currency_portfolio(currency).available == initial_available + amount
    assert portfolio_manager.portfolio.get_currency_portfolio(currency).total == initial_total + amount
    
    # Test with different amount
    amount = decimal.Decimal("25")
    initial_available = portfolio_manager.portfolio.get_currency_portfolio(currency).available
    initial_total = portfolio_manager.portfolio.get_currency_portfolio(currency).total
    await portfolio_manager.handle_balance_update_from_deposit(amount, currency)
    assert portfolio_manager.portfolio.get_currency_portfolio(currency).available == initial_available + amount
    assert portfolio_manager.portfolio.get_currency_portfolio(currency).total == initial_total + amount
    
    # Test when not simulating - should raise NotSupported error
    trader.simulate = False
    with pytest.raises(errors.NotSupported):
        await portfolio_manager.handle_balance_update_from_deposit(amount, currency)


async def test_refresh_simulated_trader_portfolio_from_order(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    if os.getenv('CYTHON_IGNORE'):
        return
    order = BuyLimitOrder(trader)
    order.symbol = "BTC/USDT"
    await order.initialize()
    with patch.object(portfolio_manager.portfolio, 'update_portfolio_available',
                      new=Mock()) as update_portfolio_available_mock:
        update_portfolio_available_mock.assert_not_called()
        portfolio_manager._enable_portfolio_total_update_from_order = False  # force _enable_portfolio_total_update_from_order to False to ensure no side effect
        assert portfolio_manager.enable_portfolio_available_update_from_order is True
        portfolio_manager._refresh_simulated_trader_portfolio_from_order(order)
        update_portfolio_available_mock.assert_called_once()
        update_portfolio_available_mock.reset_mock()
        portfolio_manager.enable_portfolio_available_update_from_order = False
        portfolio_manager._refresh_simulated_trader_portfolio_from_order(order)
        update_portfolio_available_mock.assert_not_called()
        portfolio_manager.enable_portfolio_available_update_from_order = True
        # restore _enable_portfolio_total_update_from_order
        portfolio_manager._enable_portfolio_total_update_from_order = True

    price = decimal_random_price()
    order.update(
        price=decimal_random_price(),
        quantity=decimal_random_quantity(max_value=DEFAULT_MARKET_QUANTITY / price),
        symbol="BTC/USDT"
    )
    await order.on_fill(force_fill=True)
    assert order.is_filled()

    with patch.object(portfolio_manager.portfolio, 'update_portfolio_from_filled_order',
                      new=Mock()) as update_portfolio_from_filled_order_mock:
        update_portfolio_from_filled_order_mock.assert_not_called()
        portfolio_manager.enable_portfolio_available_update_from_order = False  # force enable_portfolio_total_update_from_order to False to ensure no side effect
        assert portfolio_manager._enable_portfolio_total_update_from_order is True
        portfolio_manager._refresh_simulated_trader_portfolio_from_order(order)
        update_portfolio_from_filled_order_mock.assert_called_once()
        update_portfolio_from_filled_order_mock.reset_mock()
        portfolio_manager._enable_portfolio_total_update_from_order = False
        portfolio_manager._refresh_simulated_trader_portfolio_from_order(order)
        update_portfolio_from_filled_order_mock.assert_not_called()
        portfolio_manager._enable_portfolio_total_update_from_order = True
        # restore enable_portfolio_available_update_from_order
        portfolio_manager.enable_portfolio_available_update_from_order = True


async def test_load_simulated_portfolio_from_history(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    portfolio_manager.historical_portfolio_value_manager = mock.Mock(
        historical_ending_portfolio={
            "BTC": {
                commons_constants.PORTFOLIO_AVAILABLE: 1,
                commons_constants.PORTFOLIO_TOTAL: 10.11,
            },
            "ETH": {
                commons_constants.PORTFOLIO_AVAILABLE: -1,
                commons_constants.PORTFOLIO_TOTAL: 10,
            },
            "USDT": {
                commons_constants.PORTFOLIO_AVAILABLE: 34,
                commons_constants.PORTFOLIO_TOTAL: 34,
            }
        },
        stop=mock.AsyncMock()
    )
    portfolio_manager._load_simulated_portfolio_from_history()
    # ensure only the total value is loaded in simulated portfolio
    assert portfolio_manager.portfolio.portfolio == {
        "BTC": personal_data.SpotAsset("BTC", decimal.Decimal("10.11"), decimal.Decimal("10.11")),
        "ETH": personal_data.SpotAsset("ETH", decimal.Decimal("10"), decimal.Decimal("10")),
        "USDT": personal_data.SpotAsset("USDT", decimal.Decimal("34"), decimal.Decimal("34"))
    }
