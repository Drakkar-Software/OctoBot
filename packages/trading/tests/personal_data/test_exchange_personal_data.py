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
import asyncio
import contextlib

import mock
import pytest
from mock import patch, Mock, AsyncMock
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data as personal_data

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

pytestmark = pytest.mark.asyncio


async def test_handle_portfolio_and_position_update_from_order(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    exchange_personal_data = exchange_manager.exchange_personal_data
    portfolio_manager = exchange_personal_data.portfolio_manager

    trader.simulate = False
    order = personal_data.BuyMarketOrder(trader)
    order.update("BTC/USDT", quantity=decimal.Decimal(10), price=decimal.Decimal(100))
    
    # Create a local implementation of PortfolioUpdateEvent for testing
    class TestPortfolioUpdateEvent(personal_data.PortfolioUpdateEvent):
        def __init__(self, is_resolved_value: bool = False):
            super().__init__()
            self._is_resolved_value = is_resolved_value
        
        def is_resolved(self, updated_portfolio):
            return self._is_resolved_value
    
    with patch.object(portfolio_manager, 'handle_balance_update_from_order',
                      new=AsyncMock(return_value=(True, None))) as handle_balance_update_from_order_mock, \
         patch.object(exchange_personal_data, 'handle_portfolio_update_notification',
                      new=AsyncMock()) as handle_portfolio_update_notification_mock, \
         patch.object(exchange_personal_data, 'handle_position_instance_update',
                      new=AsyncMock()) as handle_position_instance_update_mock, \
         patch.object(exchange_personal_data.positions_manager, 'handle_position_update_from_order',
                      new=AsyncMock(return_value=True)) as handle_position_update_from_order_mock, \
         patch.object(exchange_personal_data.positions_manager, 'get_order_position',
                      new=Mock(return_value=None)) as get_order_position_mock:
        
        # Test basic case - no event returned, not futures
        exchange_manager.is_future = False
        result = await exchange_personal_data.handle_portfolio_and_position_update_from_order(
            order, require_exchange_update=True, expect_filled_order_update=False, should_notify=True
        )
        assert result is True
        handle_balance_update_from_order_mock.assert_called_once_with(order, True, False)
        handle_portfolio_update_notification_mock.assert_called_once()
        handle_position_update_from_order_mock.assert_not_called()
        handle_position_instance_update_mock.assert_not_called()
        
        # Reset mocks
        handle_balance_update_from_order_mock.reset_mock()
        handle_portfolio_update_notification_mock.reset_mock()
        
        # Test with should_notify=False
        result = await exchange_personal_data.handle_portfolio_and_position_update_from_order(
            order, require_exchange_update=True, expect_filled_order_update=False, should_notify=False
        )
        assert result is True
        handle_balance_update_from_order_mock.assert_called_once_with(order, True, False)
        handle_portfolio_update_notification_mock.assert_not_called()
        
        # Reset mocks
        handle_balance_update_from_order_mock.reset_mock()
        
        # Test with event that is already set (should not wait)
        event_set = TestPortfolioUpdateEvent(is_resolved_value=True)
        event_set.set()
        handle_balance_update_from_order_mock.return_value = (True, event_set)
        with patch.object(asyncio, 'wait_for', new=AsyncMock()) as wait_for_mock:
            result = await exchange_personal_data.handle_portfolio_and_position_update_from_order(
                order, require_exchange_update=True, expect_filled_order_update=True, should_notify=False
            )
            assert result is True
            handle_balance_update_from_order_mock.assert_called_once_with(order, True, True)
            assert event_set.is_set()
            # Verify that wait_for was not called since the event is already set
            wait_for_mock.assert_not_called()
        
        # Reset mocks
        handle_balance_update_from_order_mock.reset_mock()
        
        # Test with event that needs to wait (expect_filled_order_update=True, event not set)
        event_not_set = TestPortfolioUpdateEvent(is_resolved_value=False)
        handle_balance_update_from_order_mock.return_value = (True, event_not_set)
        
        # Set the event in a background task to simulate it being resolved
        async def set_event_after_delay():
            await asyncio.sleep(0.01)
            event_not_set.set()
        
        asyncio.create_task(set_event_after_delay())
        
        with patch.object(asyncio, 'wait_for', wraps=asyncio.wait_for) as wait_for_mock:
            result = await exchange_personal_data.handle_portfolio_and_position_update_from_order(
                order, require_exchange_update=True, expect_filled_order_update=True, should_notify=False
            )
            assert result is True
            handle_balance_update_from_order_mock.assert_called_once_with(order, True, True)
            assert event_not_set.is_set()
            # Verify that wait_for was called with event.wait() and the timeout
            wait_for_mock.assert_called_once()
            call_args = wait_for_mock.call_args
            # First argument should be event.wait() coroutine, second should be timeout
            assert call_args.kwargs['timeout'] == constants.EXPECTED_PORTFOLIO_UPDATE_TIMEOUT
        
        # Reset mocks
        handle_balance_update_from_order_mock.reset_mock()
        
        # Test with futures exchange
        exchange_manager.is_future = True
        mock_position = Mock()
        get_order_position_mock.return_value = mock_position
        handle_balance_update_from_order_mock.return_value = (True, None)
        result = await exchange_personal_data.handle_portfolio_and_position_update_from_order(
            order, require_exchange_update=True, expect_filled_order_update=False, should_notify=True
        )
        assert result is True
        handle_balance_update_from_order_mock.assert_called_once_with(order, True, False)
        handle_position_update_from_order_mock.assert_called_once_with(order, True)
        handle_portfolio_update_notification_mock.assert_called_once()
        get_order_position_mock.assert_called_once_with(order)
        handle_position_instance_update_mock.assert_called_once_with(mock_position, should_notify=True)
        
        # Reset mocks
        handle_balance_update_from_order_mock.reset_mock()
        handle_position_update_from_order_mock.reset_mock()
        handle_portfolio_update_notification_mock.reset_mock()
        handle_position_instance_update_mock.reset_mock()
        get_order_position_mock.reset_mock()
        
        # Test with futures when position update returns False
        handle_position_update_from_order_mock.return_value = False
        result = await exchange_personal_data.handle_portfolio_and_position_update_from_order(
            order, require_exchange_update=True, expect_filled_order_update=False, should_notify=False
        )
        assert result is False  # changed should be False because position update returned False
        handle_balance_update_from_order_mock.assert_called_once_with(order, True, False)
        handle_position_update_from_order_mock.assert_called_once_with(order, True)
        
        # Reset mocks and restore is_future
        exchange_manager.is_future = False
        handle_balance_update_from_order_mock.reset_mock()
        handle_position_update_from_order_mock.reset_mock()
        
        # Test AttributeError exception handling
        handle_balance_update_from_order_mock.side_effect = AttributeError("Test error")
        result = await exchange_personal_data.handle_portfolio_and_position_update_from_order(
            order, require_exchange_update=True, expect_filled_order_update=False, should_notify=False
        )
        assert result is False


async def test_handle_portfolio_update_from_withdrawal(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    exchange_personal_data = exchange_manager.exchange_personal_data
    portfolio_manager = exchange_personal_data.portfolio_manager

    amount = decimal.Decimal("10")
    currency = "USDT"
    transaction = {
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount,
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: currency,
        enums.ExchangeConstantsTransactionColumns.NETWORK.value: "bitcoin",
        enums.ExchangeConstantsTransactionColumns.TXID.value: "test_tx_id_123",
        enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value: "test_address",
        enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value: "exchange_address",
        enums.ExchangeConstantsTransactionColumns.STATUS.value: enums.BlockchainTransactionStatus.SUCCESS.value,
        enums.ExchangeConstantsTransactionColumns.FEE.value: {"USDT": decimal.Decimal("0.1")}
    }
    
    # Create a local implementation of PortfolioUpdateEvent for testing
    class TestPortfolioUpdateEvent(personal_data.PortfolioUpdateEvent):
        def __init__(self, is_resolved_value: bool = False):
            super().__init__()
            self._is_resolved_value = is_resolved_value
        
        def is_resolved(self, updated_portfolio):
            return self._is_resolved_value
    
    import octobot_trading.personal_data.transactions.transaction_factory as transaction_factory
    
    with patch.object(portfolio_manager, 'handle_balance_update_from_withdrawal',
                      new=AsyncMock(return_value=(True, None))) as handle_balance_update_from_withdrawal_mock, \
         patch.object(exchange_personal_data, 'handle_portfolio_update_notification',
                      new=AsyncMock()) as handle_portfolio_update_notification_mock, \
         patch.object(transaction_factory, 'create_blockchain_transaction',
                      new=Mock()) as create_blockchain_transaction_mock:
        
        # Test basic case - no event returned
        result = await exchange_personal_data.handle_portfolio_update_from_withdrawal(
            transaction, expect_withdrawal_update=False, should_notify=True
        )
        assert result is True
        handle_balance_update_from_withdrawal_mock.assert_called_once_with(transaction, False)
        create_blockchain_transaction_mock.assert_called_once()
        assert create_blockchain_transaction_mock.call_args[0] == (
            exchange_manager,
            currency,
            amount,
            transaction[enums.ExchangeConstantsTransactionColumns.NETWORK.value],
            transaction[enums.ExchangeConstantsTransactionColumns.TXID.value],
            enums.TransactionType.BLOCKCHAIN_WITHDRAWAL,
        )
        assert create_blockchain_transaction_mock.call_args.kwargs == {
            'destination_address': transaction[enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value],
            'blockchain_transaction_status': transaction[enums.ExchangeConstantsTransactionColumns.STATUS.value],
            'source_address': transaction[enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value],
            'transaction_fee': transaction[enums.ExchangeConstantsTransactionColumns.FEE.value],
        }
        handle_portfolio_update_notification_mock.assert_called_once()
        
        # Reset mocks
        handle_balance_update_from_withdrawal_mock.reset_mock()
        create_blockchain_transaction_mock.reset_mock()
        handle_portfolio_update_notification_mock.reset_mock()
        
        # Test with should_notify=False
        result = await exchange_personal_data.handle_portfolio_update_from_withdrawal(
            transaction, expect_withdrawal_update=False, should_notify=False
        )
        assert result is True
        handle_balance_update_from_withdrawal_mock.assert_called_once_with(transaction, False)
        create_blockchain_transaction_mock.assert_called_once()
        handle_portfolio_update_notification_mock.assert_not_called()
        
        # Reset mocks
        handle_balance_update_from_withdrawal_mock.reset_mock()
        create_blockchain_transaction_mock.reset_mock()
        
        # Test with event that is already set (should not wait)
        event_set = TestPortfolioUpdateEvent(is_resolved_value=True)
        event_set.set()
        handle_balance_update_from_withdrawal_mock.return_value = (True, event_set)
        with patch.object(asyncio, 'wait_for', new=AsyncMock()) as wait_for_mock:
            result = await exchange_personal_data.handle_portfolio_update_from_withdrawal(
                transaction, expect_withdrawal_update=True, should_notify=False
            )
            assert result is True
            handle_balance_update_from_withdrawal_mock.assert_called_once_with(transaction, True)
            assert event_set.is_set()
            # Verify that wait_for was not called since the event is already set
            wait_for_mock.assert_not_called()
            create_blockchain_transaction_mock.assert_called_once()
        
        # Reset mocks
        handle_balance_update_from_withdrawal_mock.reset_mock()
        create_blockchain_transaction_mock.reset_mock()
        
        # Test with event that needs to wait (expect_withdrawal_update=True, event not set)
        event_not_set = TestPortfolioUpdateEvent(is_resolved_value=False)
        handle_balance_update_from_withdrawal_mock.return_value = (True, event_not_set)
        
        # Set the event in a background task to simulate it being resolved
        async def set_event_after_delay():
            await asyncio.sleep(0.01)
            event_not_set.set()
        
        asyncio.create_task(set_event_after_delay())
        
        with patch.object(asyncio, 'wait_for', wraps=asyncio.wait_for) as wait_for_mock:
            result = await exchange_personal_data.handle_portfolio_update_from_withdrawal(
                transaction, expect_withdrawal_update=True, should_notify=False
            )
            assert result is True
            handle_balance_update_from_withdrawal_mock.assert_called_once_with(transaction, True)
            assert event_not_set.is_set()
            # Verify that wait_for was called with event.wait() and the timeout
            wait_for_mock.assert_called_once()
            call_args = wait_for_mock.call_args
            # Verify timeout parameter
            assert call_args.kwargs['timeout'] == constants.EXPECTED_PORTFOLIO_UPDATE_TIMEOUT
            create_blockchain_transaction_mock.assert_called_once()
        
        # Reset mocks
        handle_balance_update_from_withdrawal_mock.reset_mock()
        create_blockchain_transaction_mock.reset_mock()
        
        # Test when handle_balance_update_from_withdrawal returns False
        handle_balance_update_from_withdrawal_mock.return_value = (False, None)
        result = await exchange_personal_data.handle_portfolio_update_from_withdrawal(
            transaction, expect_withdrawal_update=False, should_notify=False
        )
        assert result is False
        handle_balance_update_from_withdrawal_mock.assert_called_once_with(transaction, False)
        create_blockchain_transaction_mock.assert_called_once()  # Still creates transaction even if changed=False


async def test_handle_portfolio_update(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    exchange_personal_data = exchange_manager.exchange_personal_data
    portfolio_manager = exchange_personal_data.portfolio_manager

    balance = {
        "BTC": {
            "available": decimal.Decimal("10"),
            "total": decimal.Decimal("10")
        },
        "USDT": {
            "available": decimal.Decimal("1000"),
            "total": decimal.Decimal("1000")
        }
    }
    
    portfolio_history_update_mock = mock.AsyncMock()
    # Create a mock async context manager
    @contextlib.asynccontextmanager
    async def mock_portfolio_history_update():
        await portfolio_history_update_mock()
        yield
    
    with patch.object(portfolio_manager, 'handle_balance_update',
                      new=Mock(return_value=True)) as handle_balance_update_mock, \
         patch.object(exchange_personal_data, 'resolve_pending_portfolio_update_events',
                      new=AsyncMock()) as resolve_pending_portfolio_update_events_mock, \
         patch.object(exchange_personal_data, 'handle_portfolio_update_notification',
                      new=AsyncMock()) as handle_portfolio_update_notification_mock, \
         patch.object(portfolio_manager, 'portfolio_history_update',
                      new=mock_portfolio_history_update):
        
        # Test basic case with should_notify=True
        result = await exchange_personal_data.handle_portfolio_update(balance, should_notify=True, is_diff_update=False)
        assert result is True
        handle_balance_update_mock.assert_called_once_with(balance, is_diff_update=False)
        resolve_pending_portfolio_update_events_mock.assert_called_once()
        handle_portfolio_update_notification_mock.assert_called_once_with(balance)
        portfolio_history_update_mock.assert_called_once()
        
        # Reset mocks
        handle_balance_update_mock.reset_mock()
        resolve_pending_portfolio_update_events_mock.reset_mock()
        handle_portfolio_update_notification_mock.reset_mock()
        portfolio_history_update_mock.reset_mock()
        
        # Test with should_notify=False
        result = await exchange_personal_data.handle_portfolio_update(balance, should_notify=False, is_diff_update=False)
        assert result is True
        handle_balance_update_mock.assert_called_once_with(balance, is_diff_update=False)
        resolve_pending_portfolio_update_events_mock.assert_called_once()
        handle_portfolio_update_notification_mock.assert_not_called()
        portfolio_history_update_mock.assert_called_once()
        
        # Reset mocks
        handle_balance_update_mock.reset_mock()
        resolve_pending_portfolio_update_events_mock.reset_mock()
        portfolio_history_update_mock.reset_mock()
        
        # Test with is_diff_update=True
        result = await exchange_personal_data.handle_portfolio_update(balance, should_notify=False, is_diff_update=True)
        assert result is True
        handle_balance_update_mock.assert_called_once_with(balance, is_diff_update=True)
        resolve_pending_portfolio_update_events_mock.assert_called_once()
        portfolio_history_update_mock.assert_called_once()
        
        # Reset mocks
        handle_balance_update_mock.reset_mock()
        resolve_pending_portfolio_update_events_mock.reset_mock()
        portfolio_history_update_mock.reset_mock()
        
        # Test when handle_balance_update returns False
        handle_balance_update_mock.return_value = False
        result = await exchange_personal_data.handle_portfolio_update(balance, should_notify=False, is_diff_update=False)
        assert result is False
        handle_balance_update_mock.assert_called_once_with(balance, is_diff_update=False)
        resolve_pending_portfolio_update_events_mock.assert_called_once()
        portfolio_history_update_mock.assert_called_once()
        
        # Reset mocks
        handle_balance_update_mock.reset_mock()
        resolve_pending_portfolio_update_events_mock.reset_mock()
        portfolio_history_update_mock.reset_mock()
        
        # Test AttributeError exception handling
        handle_balance_update_mock.side_effect = AttributeError("Test error")
        result = await exchange_personal_data.handle_portfolio_update(balance, should_notify=False, is_diff_update=False)
        assert result is False
        handle_balance_update_mock.assert_called_once_with(balance, is_diff_update=False)
        resolve_pending_portfolio_update_events_mock.assert_not_called()  # Should not be called if exception occurs
        portfolio_history_update_mock.assert_called_once()
