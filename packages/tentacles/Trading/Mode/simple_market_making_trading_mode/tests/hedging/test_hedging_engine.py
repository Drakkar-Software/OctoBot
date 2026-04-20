import pytest
import mock
import decimal
import asyncio
import contextlib

import octobot_commons.symbols as symbols_util
import octobot_commons.asyncio_tools as asyncio_tools
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.hedging_engine as hedging_engine_import
import octobot_trading.api as trading_api
import octobot_trading.exchanges
import octobot_trading.personal_data
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.errors as hedging_errors
import tentacles.Automation.trigger_events.volatility_threshold_event.volatility_threshold as volatility_threshold

import tentacles.Trading.Mode.simple_market_making_trading_mode.tests.hedging as hedging_tests
from tentacles.Trading.Mode.simple_market_making_trading_mode.tests.hedging import (
    SYMBOL,
    order_book_distribution,
    create_hedging_fill,
    create_hedging_order,
)

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@contextlib.asynccontextmanager
async def hedging_engine_context():
    async with hedging_tests.exchange_manager_context() as exchange_manager:
        yield hedging_engine_import.HedgingEngine(
            trading_exchange_manager=exchange_manager,
            hedging_exchange_name="hedgex",
        )


@contextlib.asynccontextmanager
async def hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, symbol=SYMBOL, mock_async_start_for_hedging_details=True):
    async with hedging_engine_context() as hedging_engine:
        # use the same exchange manager to simplify testing
        hedging_engine._hedging_exchange_manager = hedging_engine._trading_exchange_manager
        with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
            hedging_engine.register_symbol(
                symbol=symbol,
                hedging_profit_threshold=decimal.Decimal("0.01"),
                hedging_max_loss_threshold=decimal.Decimal("0.01"),
                order_book_distribution=order_book_distribution,
                max_positive_percent_price_change=40,
                max_negative_percent_price_change=12,
                average_price_counted_minutes=10,
            )
            if mock_async_start_for_hedging_details:
                yield hedging_engine
        if not mock_async_start_for_hedging_details:
            yield hedging_engine


def create_order_group_with_orders(exchange_manager, group_name, exchange_order_ids):
    """Helper function to create a OneCancelsTheOtherOrderGroup with orders."""
    orders_manager = mock.Mock()
    orders = []
    for exchange_order_id in exchange_order_ids:
        order = create_hedging_order(exchange_manager, exchange_order_id)
        # Mock order methods to make it appear "open"
        order.is_open = mock.Mock(return_value=True)
        order.is_cancelling = mock.Mock(return_value=False)
        order.is_synchronization_enabled = mock.Mock(return_value=True)
        order.is_filled = mock.Mock(return_value=False)
        order.is_closed = mock.Mock(return_value=False)
        orders.append(order)
    
    orders_manager.get_order_from_group = mock.Mock(return_value=orders)
    order_group = exchange_manager.exchange_personal_data.orders_manager.create_group(
        octobot_trading.personal_data.OneCancelsTheOtherOrderGroup, group_name=group_name
    )
    order_group.get_group_open_orders = mock.Mock(return_value=orders)
    return order_group


def register_fill(hedging_engine, fill, order_exchange_id=None):
    """Helper function to register a fill to hedging details."""
    if order_exchange_id is None:
        order_exchange_id = fill.fill_trade.exchange_order_id
    details = hedging_engine.get_symbol_details(fill.fill_trade.symbol)
    if order_exchange_id not in details.hedging_fills_by_order_id:
        details.hedging_fills_by_order_id[order_exchange_id] = []
    details.hedging_fills_by_order_id[order_exchange_id].append(fill)


async def test__init__():
    async with hedging_engine_context() as hedging_engine:
        assert isinstance(hedging_engine._trading_exchange_manager, octobot_trading.exchanges.ExchangeManager)
        assert hedging_engine.hedging_exchange_name == "hedgex"
        assert hedging_engine._consumers == []
        assert hedging_engine._hedging_details_by_symbol == {}
        assert hedging_engine._logger is not None


@pytest.mark.asyncio
async def test_register_symbol(order_book_distribution):
    async with hedging_engine_context() as hedging_engine:
        with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()) as mock_async_start_for_hedging_details:
            hedging_engine.register_symbol(
                symbol=SYMBOL,
                hedging_profit_threshold=decimal.Decimal("0.01"),
                hedging_max_loss_threshold=decimal.Decimal("0.01"),
                order_book_distribution=order_book_distribution,
                max_positive_percent_price_change=40,
                max_negative_percent_price_change=12,
                average_price_counted_minutes=10,
            )
            assert isinstance(hedging_engine._hedging_details_by_symbol["BTC/USDT"], hedging_engine_import.SymbolHedgingDetails)
            details = hedging_engine._hedging_details_by_symbol["BTC/USDT"]
            assert details.symbol == symbols_util.parse_symbol(SYMBOL)
            assert details.state == hedging_engine_import.HedgingEngineState.PENDING_START
            assert details.hedging_profit_threshold == decimal.Decimal("0.01")
            assert details.hedging_max_loss_threshold == decimal.Decimal("0.01")
            assert details.order_book_distribution == order_book_distribution
            assert details.volatility_threshold_checker.symbol == SYMBOL
            assert details.volatility_threshold_checker.period_in_minutes == 10
            assert details.volatility_threshold_checker.max_allowed_positive_percentage_change == decimal.Decimal("40")
            assert details.volatility_threshold_checker.max_allowed_negative_percentage_change == decimal.Decimal("12")
            assert mock_async_start_for_hedging_details.call_count == 1
            assert len(hedging_engine._start_tasks) == 1
            assert isinstance(hedging_engine._start_tasks[0], asyncio.Task)


async def test_hedge_filled_or_partially_filled_order(order_book_distribution):
    async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
        # Create order dict
        order_dict = {
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123"
        }

        fill = create_hedging_fill(
            trading_exchange_manager=hedging_engine._trading_exchange_manager,
            order_exchange_id="trading_order_456",
            hedging_order=None
        )
        with mock.patch.object(hedging_engine, "_register_hedging_fill", return_value=fill) as _register_hedging_fill_order:
            with pytest.raises(NotImplementedError):
                await hedging_engine.hedge_filled_or_partially_filled_order(order_dict)
            _register_hedging_fill_order.assert_called_once_with(order_dict)
            assert fill.hedging_order is None


class TestGetOrderAssociatedHedgingFill:
    """Test class for _get_order_associated_hedging_fill method."""

    async def test_finds_by_exchange_order_id(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a real hedging order
            hedging_order = create_hedging_order(
                hedging_engine._trading_exchange_manager,
                exchange_order_id="hedge_order_123",
                order_group=None,
            )
            
            # Create and register a hedging fill with the hedging order
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                hedging_order=hedging_order,
            )
            register_fill(hedging_engine, fill)
            
            # Create order dict matching the hedging order's exchange_order_id
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_order_123",
            }
            
            # Test that the fill is found
            result = hedging_engine._get_order_associated_hedging_fill(order_dict)
            assert result is fill

    async def test_finds_by_order_group(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a real order group with orders
            order_group = create_order_group_with_orders(
                hedging_engine._hedging_exchange_manager,
                "test_group",
                ["group_order_1", "group_order_2", "group_order_3"],
            )
            
            # Create a real hedging order with order group
            hedging_order = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_123",
                order_group=order_group,
            )
            
            # Create and register a hedging fill with the hedging order
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                hedging_order=hedging_order,
            )
            register_fill(hedging_engine, fill)
            
            # Create order dict matching one of the group orders
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "group_order_2",
            }
            
            # Test that the fill is found via order group
            result = hedging_engine._get_order_associated_hedging_fill(order_dict)
            assert result is fill

    async def test_not_found_when_no_match(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a real hedging order
            hedging_order = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_123",
                order_group=None,
            )
            
            # Create and register a hedging fill with the hedging order
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                hedging_order=hedging_order,
            )
            register_fill(hedging_engine, fill)
            
            # Create order dict that doesn't match
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "unknown_order_999",
            }
            
            # Test that no fill is found
            result = hedging_engine._get_order_associated_hedging_fill(order_dict)
            assert result is None

    async def test_not_found_when_hedging_order_is_none(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create and register a hedging fill without hedging_order
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                hedging_order=None,
            )
            register_fill(hedging_engine, fill)
            
            # Create order dict
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "any_order_123",
            }
            
            # Test that no fill is found when hedging_order is None
            result = hedging_engine._get_order_associated_hedging_fill(order_dict)
            assert result is None

    async def test_with_multiple_symbols(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            # use the same exchange manager to simplify testing
            hedging_engine._hedging_exchange_manager = hedging_engine._trading_exchange_manager
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register two symbols
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                hedging_engine.register_symbol(
                    symbol="ETH/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                
                # Create fills for both symbols
                hedging_order_btc = create_hedging_order(
                    hedging_engine._hedging_exchange_manager,
                    exchange_order_id="hedge_btc_123",
                    order_group=None,
                )
                
                hedging_order_eth = create_hedging_order(
                    hedging_engine._hedging_exchange_manager,
                    exchange_order_id="hedge_eth_456",
                    order_group=None,
                )
                
                fill_btc = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="trading_btc_789",
                    symbol="BTC/USDT",
                    hedging_order=hedging_order_btc,
                )
                
                fill_eth = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="trading_eth_012",
                    symbol="ETH/USDT",
                    side=trading_enums.TradeOrderSide.SELL,
                    filled_price=decimal.Decimal("500"),
                    hedging_price=decimal.Decimal("501"),
                    locally_filled_amount=decimal.Decimal("0.2"),
                    filled_time=1234567891.0,
                    hedging_order=hedging_order_eth,
                )
                
                # Register fills to respective hedging details
                register_fill(hedging_engine, fill_btc)
                register_fill(hedging_engine, fill_eth)
                
                # Test finding BTC fill
                order_dict_btc = {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_btc_123",
                }
                result_btc = hedging_engine._get_order_associated_hedging_fill(order_dict_btc)
                assert result_btc is fill_btc
                assert result_btc.fill_trade.symbol == "BTC/USDT"
                
                # Test finding ETH fill
                order_dict_eth = {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_eth_456",
                }
                result_eth = hedging_engine._get_order_associated_hedging_fill(order_dict_eth)
                assert result_eth is fill_eth
                assert result_eth.fill_trade.symbol == "ETH/USDT"

    async def test_with_multiple_fills_per_order(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create multiple fills for the same trading order (partial fills)
            hedging_order_1 = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_1",
                order_group=None,
            )
            
            hedging_order_2 = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_2",
                order_group=None,
            )
            
            fill_1 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                locally_filled_amount=decimal.Decimal("0.05"),
                filled_time=1234567890.0,
                hedging_order=hedging_order_1,
            )
            
            fill_2 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                locally_filled_amount=decimal.Decimal("0.05"),
                filled_time=1234567891.0,
                hedging_order=hedging_order_2,
            )
            
            # Register both fills to hedging details
            register_fill(hedging_engine, fill_1)
            register_fill(hedging_engine, fill_2)
            
            # Test finding the first fill
            order_dict_1 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_order_1",
            }
            result_1 = hedging_engine._get_order_associated_hedging_fill(order_dict_1)
            assert result_1 is fill_1
            
            # Test finding the second fill
            order_dict_2 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_order_2",
            }
            result_2 = hedging_engine._get_order_associated_hedging_fill(order_dict_2)
            assert result_2 is fill_2

    async def test_order_group_not_in_list(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a real order group that doesn't contain the order
            order_group = create_order_group_with_orders(
                hedging_engine._hedging_exchange_manager,
                "test_group",
                ["group_order_1", "group_order_2"],
            )
            
            # Create a real hedging order with order group
            hedging_order = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_123",
                order_group=order_group,
            )
            
            # Create and register a hedging fill with the hedging order
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                hedging_order=hedging_order,
            )
            register_fill(hedging_engine, fill)
            
            # Create order dict that's not in the group
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "group_order_999",
            }
            
            # Test that no fill is found
            result = hedging_engine._get_order_associated_hedging_fill(order_dict)
            assert result is None


class TestClearCompletedFills:
    """Test class for _clear_completed_fills method."""

    async def test_clears_fills_when_order_closed_and_all_unlocked(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create fills for a closed order (all unlocked)
            fill_1 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="closed_order_123",
                is_locked=False,
            )
            fill_2 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="closed_order_123",
                is_locked=False,
            )
            register_fill(hedging_engine, fill_1)
            register_fill(hedging_engine, fill_2)
            
            # Mock get_open_orders to return empty list (order is closed)
            with mock.patch.object(trading_api, "get_open_orders", return_value=[]):
                hedging_engine._clear_completed_fills()
            
            # Verify fills are cleared
            details = hedging_engine.get_symbol_details(SYMBOL)
            assert details.hedging_fills_by_order_id == {}

    async def test_keeps_fills_when_order_still_open(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create fills for an open order
            fill_1 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="open_order_123",
                is_locked=False,
            )
            fill_2 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="open_order_123",
                is_locked=False,
            )
            register_fill(hedging_engine, fill_1)
            register_fill(hedging_engine, fill_2)
            
            # Mock get_open_orders to return the open order
            open_order = create_hedging_order(
                hedging_engine._trading_exchange_manager,
                exchange_order_id="open_order_123",
            )
            with mock.patch.object(trading_api, "get_open_orders", return_value=[open_order]):
                hedging_engine._clear_completed_fills()
            
            # Verify fills are NOT cleared (order is still open)
            details = hedging_engine.get_symbol_details(SYMBOL)
            assert "open_order_123" in details.hedging_fills_by_order_id
            assert len(details.hedging_fills_by_order_id["open_order_123"]) == 2

    async def test_keeps_fills_when_at_least_one_locked(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create fills for a closed order, but one is still locked
            fill_1 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="closed_order_456",
                is_locked=False,
            )
            fill_2 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="closed_order_456",
                is_locked=True,  # Still locked
            )
            register_fill(hedging_engine, fill_1)
            register_fill(hedging_engine, fill_2)
            
            # Mock get_open_orders to return empty list (order is closed)
            with mock.patch.object(trading_api, "get_open_orders", return_value=[]):
                hedging_engine._clear_completed_fills()
            
            # Verify fills are NOT cleared (at least one is still locked)
            details = hedging_engine.get_symbol_details(SYMBOL)
            assert "closed_order_456" in details.hedging_fills_by_order_id
            assert len(details.hedging_fills_by_order_id["closed_order_456"]) == 2

    async def test_clears_multiple_orders_selectively(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create fills for multiple orders with different states
            # Order 1: closed and all unlocked (should be cleared)
            fill_1a = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="closed_unlocked_1",
                is_locked=False,
            )
            fill_1b = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="closed_unlocked_1",
                is_locked=False,
            )
            register_fill(hedging_engine, fill_1a)
            register_fill(hedging_engine, fill_1b)
            
            # Order 2: closed but still locked (should NOT be cleared)
            fill_2 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="closed_locked_2",
                is_locked=True,
            )
            register_fill(hedging_engine, fill_2)
            
            # Order 3: still open (should NOT be cleared)
            fill_3 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="open_order_3",
                is_locked=False,
            )
            register_fill(hedging_engine, fill_3)
            
            # Mock get_open_orders to return only the open order
            open_order = create_hedging_order(
                hedging_engine._trading_exchange_manager,
                exchange_order_id="open_order_3",
            )
            with mock.patch.object(trading_api, "get_open_orders", return_value=[open_order]):
                hedging_engine._clear_completed_fills()
            
            # Verify only the closed+unlocked order is cleared
            details = hedging_engine.get_symbol_details(SYMBOL)
            assert len(details.hedging_fills_by_order_id) == 2
            assert "closed_unlocked_1" not in details.hedging_fills_by_order_id
            assert "closed_locked_2" in details.hedging_fills_by_order_id
            assert "open_order_3" in details.hedging_fills_by_order_id

    async def test_clears_fills_across_multiple_symbols(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register two symbols
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                hedging_engine.register_symbol(
                    symbol="ETH/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                
                # Create fills for both symbols
                fill_btc = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="btc_order_123",
                    symbol="BTC/USDT",
                    is_locked=False,
                )
                fill_eth = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="eth_order_456",
                    symbol="ETH/USDT",
                    is_locked=False,
                )
                register_fill(hedging_engine, fill_btc)
                register_fill(hedging_engine, fill_eth)
                
                # Mock get_open_orders to return empty list (all orders closed)
                with mock.patch.object(trading_api, "get_open_orders", return_value=[]):
                    hedging_engine._clear_completed_fills()
                
                # Verify fills are cleared for both symbols
                details_btc = hedging_engine.get_symbol_details("BTC/USDT")
                details_eth = hedging_engine.get_symbol_details("ETH/USDT")
                assert "btc_order_123" not in details_btc.hedging_fills_by_order_id
                assert "eth_order_456" not in details_eth.hedging_fills_by_order_id
                assert details_btc.hedging_fills_by_order_id == {}
                assert details_eth.hedging_fills_by_order_id == {}

    async def test_handles_empty_fills_dict(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # No fills registered
            details = hedging_engine.get_symbol_details(SYMBOL)
            assert len(details.hedging_fills_by_order_id) == 0
            
            # Mock get_open_orders
            with mock.patch.object(trading_api, "get_open_orders", return_value=[]):
                # Should not raise an error
                hedging_engine._clear_completed_fills()
            
            # Verify still empty
            assert len(details.hedging_fills_by_order_id) == 0


class TestOnHedgingOrderFilled:
    """Test class for _on_hedging_order_filled method."""

    async def test_unlocks_fill_and_calls_clear_when_fill_found(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a hedging order and fill
            hedging_order = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_123",
            )
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_456",
                hedging_order=hedging_order,
                hedging_price=decimal.Decimal("1025"),
                is_locked=True,
            )
            register_fill(hedging_engine, fill)
            
            # Create order dict for the filled hedging order
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_order_123",
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: "0.1",
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "1025",
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
                trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
            }
            
            # Mock _clear_completed_fills to verify it's called
            with mock.patch.object(hedging_engine, "_clear_completed_fills") as mock_clear, \
                mock.patch.object(hedging_engine._logger, "info") as mock_info:
                hedging_engine._on_hedging_order_filled(order_dict)
            
            # Verify fill is unlocked
            assert fill.is_locked is False
            # Verify _clear_completed_fills was called
            mock_clear.assert_called_once()

            # Verify info was logged
            assert mock_info.call_count == 2
            log_message_1 = mock_info.mock_calls[0].args[0]
            assert "hedge_order_123" in log_message_1
            assert "fill: unlocking" in log_message_1
            
            log_message_2 = mock_info.mock_calls[1].args[0]
            assert "Completed hedging fill" in log_message_2
            assert "[Stop triggered] " not in log_message_2
            assert "Profits: +2.2975 USDT" in log_message_2
            assert "buy 0.1 BTC/USDT at 1000" in log_message_2
            assert "total: 100.0 USDT" in log_message_2
            assert "hedged with sell 0.1 BTC at 1025" in log_message_2
            assert "total: 102.5 USDT" in log_message_2
            assert "Fees: Total: 0.2025 USDT" in log_message_2
            assert "trading: 0.0001 BTC (= 0.1000 USDT) [estimated]" in log_message_2
            assert "hedging: 0.1025 USDT [estimated]" in log_message_2
            assert "[binance]" in log_message_2
            assert "trading_order_456" in log_message_2

    async def test_logs_warning_and_does_not_call_clear_when_fill_not_found(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create order dict for an order that doesn't exist
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "unknown_order_999",
            }
            
            # Mock logger to verify warning is logged
            with mock.patch.object(hedging_engine._logger, "warning") as mock_warning, \
                 mock.patch.object(hedging_engine, "_clear_completed_fills") as mock_clear:
                hedging_engine._on_hedging_order_filled(order_dict)
            
            # Verify warning was logged
            mock_warning.assert_called_once()
            assert "No pending hedging fill found" in mock_warning.call_args[0][0]
            assert "unknown_order_999" in mock_warning.call_args[0][0]

            # Verify _clear_completed_fills was not called
            mock_clear.assert_not_called()

    async def test_logs_info_for_buy_order_unlocking_base(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a BUY order fill (should unlock base)
            hedging_order = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_buy",
            )
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_buy",
                hedging_order=hedging_order,
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.5"),
                is_locked=True,
            )
            register_fill(hedging_engine, fill)
            
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_order_buy",
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: "0.1",
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "1025",
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
                trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.STOP_LOSS.value,
            }
            
            # Mock logger to verify info message
            with mock.patch.object(hedging_engine._logger, "info") as mock_info, \
                 mock.patch.object(hedging_engine, "_clear_completed_fills"):
                hedging_engine._on_hedging_order_filled(order_dict)

            assert fill.is_locked is False
            
            # Verify info was logged with base amount
            assert mock_info.call_count == 2
            call_1_args = mock_info.mock_calls[0].args[0]
            assert "hedge_order_buy" in call_1_args
            assert "0.5" in call_1_args  # locked base amount
            assert "BTC" in call_1_args  # base currency
            assert hedging_engine._trading_exchange_manager.exchange_name in call_1_args

            call_2_args = mock_info.mock_calls[1].args[0]
            assert "Completed hedging fill" in call_2_args
            assert "[Stop triggered] " in call_2_args
            assert "Profits: +1.4875 USDT" in call_2_args
            assert "trading: 0.0005 BTC (= 0.5000 USDT)" in call_2_args
            assert "hedging: 0.5125 USDT" in call_2_args

    async def test_logs_info_for_sell_order_unlocking_quote(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a SELL order fill (should unlock quote)
            hedging_order = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_sell",
            )
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_sell",
                hedging_order=hedging_order,
                side=trading_enums.TradeOrderSide.SELL,
                locally_filled_amount=decimal.Decimal("0.3"),
                filled_price=decimal.Decimal("50000"),
                is_locked=True,
            )
            register_fill(hedging_engine, fill)
            
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "hedge_order_sell",
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: "0.1",
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "1025",
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
            }
            
            # Mock logger to verify info message
            with mock.patch.object(hedging_engine._logger, "info") as mock_info, \
                 mock.patch.object(hedging_engine, "_clear_completed_fills"):
                hedging_engine._on_hedging_order_filled(order_dict)

            assert fill.is_locked is False
            
            # Verify info was logged with quote amount
            # Verify info was logged with base amount
            assert mock_info.call_count == 2
            call_1_args = mock_info.mock_calls[0].args[0]

            assert "hedge_order_sell" in call_1_args
            # Quote amount = 0.3 * 50000 = 15000
            assert "15000" in call_1_args or "15000.0" in call_1_args
            assert "USDT" in call_1_args  # quote currency
            assert hedging_engine._trading_exchange_manager.exchange_name in call_1_args

            call_2_args = mock_info.mock_calls[1].args[0]
            assert "Completed hedging fill" in call_2_args
            assert "Profits: +4882.1925 USDT" in call_2_args
            assert "trading: 15.0000 USDT" in call_2_args
            assert "0.0003 BTC (= 0.3075 USDT)" in call_2_args

    async def test_handles_fill_found_via_order_group(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create an order group with orders
            order_group = create_order_group_with_orders(
                hedging_engine._hedging_exchange_manager,
                "test_group",
                ["group_order_1", "group_order_2"],
            )
            
            # Create hedging order with the group
            hedging_order = create_hedging_order(
                hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_group",
                order_group=order_group,
            )
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="trading_order_group",
                hedging_order=hedging_order,
                is_locked=True,
            )
            register_fill(hedging_engine, fill)
            
            # Create order dict for one of the group orders (not the hedging order itself)
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "group_order_1",
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: "0.1",
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "1025",
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
            }
            
            # Mock _clear_completed_fills to verify it's called
            with mock.patch.object(hedging_engine, "_clear_completed_fills") as mock_clear:
                hedging_engine._on_hedging_order_filled(order_dict)
            
            # Verify fill is unlocked
            assert fill.is_locked is False
            # Verify _clear_completed_fills was called
            mock_clear.assert_called_once()


class TestRegisterHedgingFill:
    """Test class for _register_hedging_fill method."""

    async def test_registers_fill_successfully(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Set hedging price
            details = hedging_engine.get_symbol_details(SYMBOL)
            details.last_hedging_price = decimal.Decimal("50000")
            
            # Create order dict
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",
            }
            
            # Register fill
            fill = hedging_engine._register_hedging_fill(order_dict)
            
            # Verify fill properties
            assert fill.fill_trade.exchange_order_id == "order_123"
            assert fill.fill_trade.symbol == SYMBOL
            assert fill.fill_trade.side == trading_enums.TradeOrderSide.BUY
            assert fill.fill_trade.executed_price == decimal.Decimal("49000")
            assert fill.hedging_price == decimal.Decimal("50000")
            assert fill.fill_trade.executed_quantity == decimal.Decimal("0.1")
            assert fill.is_locked is True
            assert fill.hedging_order is None
            
            # Verify fill is registered
            assert "order_123" in details.hedging_fills_by_order_id
            assert len(details.hedging_fills_by_order_id["order_123"]) == 1
            assert details.hedging_fills_by_order_id["order_123"][0] is fill

    async def test_raises_error_when_hedging_price_not_set(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Don't set hedging price (defaults to ZERO)
            details = hedging_engine.get_symbol_details(SYMBOL)
            assert details.last_hedging_price == trading_constants.ZERO
            
            # Create order dict
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",
            }
            
            # Should raise error
            with pytest.raises(hedging_errors.HedgingPriceNotSetError) as exc_info:
                hedging_engine._register_hedging_fill(order_dict)
            
            assert "Hedging price is not set" in str(exc_info.value)

    async def test_registers_multiple_partial_fills(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Set hedging price
            details = hedging_engine.get_symbol_details(SYMBOL)
            details.last_hedging_price = decimal.Decimal("50000")
            
            # First partial fill
            order_dict_1 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",
            }
            fill_1 = hedging_engine._register_hedging_fill(order_dict_1)
            
            # Second partial fill (total filled is now 0.2)
            order_dict_2 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.2",  # Total filled
            }
            fill_2 = hedging_engine._register_hedging_fill(order_dict_2)
            
            # Verify both fills are registered
            assert len(details.hedging_fills_by_order_id["order_123"]) == 2
            assert fill_1.fill_trade.executed_quantity == decimal.Decimal("0.1")
            assert fill_2.fill_trade.executed_quantity == decimal.Decimal("0.1")  # Newly filled amount
            assert details.hedging_fills_by_order_id["order_123"][0] is fill_1
            assert details.hedging_fills_by_order_id["order_123"][1] is fill_2

    async def test_calculates_newly_filled_amount_correctly(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Set hedging price
            details = hedging_engine.get_symbol_details(SYMBOL)
            details.last_hedging_price = decimal.Decimal("50000")
            
            # Register first fill: 0.1 filled
            order_dict_1 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",
            }
            fill_1 = hedging_engine._register_hedging_fill(order_dict_1)
            assert fill_1.fill_trade.executed_quantity == decimal.Decimal("0.1")
            
            # Register second fill: 0.25 total filled, so newly filled is 0.15
            order_dict_2 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.25",
            }
            fill_2 = hedging_engine._register_hedging_fill(order_dict_2)
            assert fill_2.fill_trade.executed_quantity == decimal.Decimal("0.15")

    async def test_handles_sell_order(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Set hedging price
            details = hedging_engine.get_symbol_details(SYMBOL)
            details.last_hedging_price = decimal.Decimal("50000")
            
            # Create SELL order dict
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "sell_order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.SELL.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "51000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.2",
            }
            
            # Register fill
            fill = hedging_engine._register_hedging_fill(order_dict)
            
            # Verify fill properties
            assert fill.fill_trade.side == trading_enums.TradeOrderSide.SELL
            assert fill.fill_trade.executed_price == decimal.Decimal("51000")
            assert fill.fill_trade.executed_quantity == decimal.Decimal("0.2")
            
            # Verify fill is registered
            assert "sell_order_123" in details.hedging_fills_by_order_id
            assert details.hedging_fills_by_order_id["sell_order_123"][0] is fill

    async def test_raises_error_when_newly_filled_amount_zero_or_negative(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Set hedging price
            details = hedging_engine.get_symbol_details(SYMBOL)
            details.last_hedging_price = decimal.Decimal("50000")
            
            # Register first fill: 0.1 filled
            order_dict_1 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",
            }
            hedging_engine._register_hedging_fill(order_dict_1)
            
            # Try to register with same filled amount (should raise error)
            order_dict_2 = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",  # Same as before
            }
            
            with pytest.raises(hedging_errors.HedgingAlreadyCountedFillAmountError) as exc_info:
                hedging_engine._register_hedging_fill(order_dict_2)
            
            assert "Newly filled amount" in str(exc_info.value)

    async def test_registers_fill_for_correct_symbol(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register two symbols
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                hedging_engine.register_symbol(
                    symbol="ETH/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                
                # Set hedging prices
                details_btc = hedging_engine.get_symbol_details("BTC/USDT")
                details_btc.last_hedging_price = decimal.Decimal("50000")
                details_eth = hedging_engine.get_symbol_details("ETH/USDT")
                details_eth.last_hedging_price = decimal.Decimal("3000")
                
                # Register fill for BTC
                order_dict_btc = {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "btc_order_123",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
                    trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                    trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",
                }
                fill_btc = hedging_engine._register_hedging_fill(order_dict_btc)
                
                # Register fill for ETH
                order_dict_eth = {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "eth_order_456",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "ETH/USDT",
                    trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "2900",
                    trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "1.0",
                }
                fill_eth = hedging_engine._register_hedging_fill(order_dict_eth)
                
                # Verify fills are registered in correct symbol details
                assert "btc_order_123" in details_btc.hedging_fills_by_order_id
                assert "eth_order_456" in details_eth.hedging_fills_by_order_id
                assert "btc_order_123" not in details_eth.hedging_fills_by_order_id
                assert "eth_order_456" not in details_btc.hedging_fills_by_order_id
                assert fill_btc.hedging_price == decimal.Decimal("50000")
                assert fill_eth.hedging_price == decimal.Decimal("3000")

    async def test_filled_time_is_set(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Set hedging price
            details = hedging_engine.get_symbol_details(SYMBOL)
            details.last_hedging_price = decimal.Decimal("50000")
            
            # Create order dict
            order_dict = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY.value,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "49000",
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value: "0.1",
            }
            
            # Register fill
            import time as time_module
            before_time = time_module.time()
            fill = hedging_engine._register_hedging_fill(order_dict)
            after_time = time_module.time()
            
            # Verify filled_time is set and within reasonable range
            assert before_time <= fill.fill_trade.executed_time <= after_time


class TestGetLockedBaseAndQuote:
    """Test class for get_locked_base_and_quote method."""

    async def test_returns_zero_when_no_fills(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # No fills registered
            locked_base, locked_quote = hedging_engine.get_locked_base_and_quote(SYMBOL)
            assert locked_base == trading_constants.ZERO
            assert locked_quote == trading_constants.ZERO

    async def test_returns_locked_base_for_buy_order(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create locked BUY fill
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="buy_order_123",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.5"),
                is_locked=True,
            )
            register_fill(hedging_engine, fill)
            
            # Get locked amounts
            locked_base, locked_quote = hedging_engine.get_locked_base_and_quote(SYMBOL)
            
            # BUY order locks base
            assert locked_base == decimal.Decimal("0.5")
            assert locked_quote == trading_constants.ZERO

    async def test_returns_locked_quote_for_sell_order(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create locked SELL fill
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="sell_order_123",
                side=trading_enums.TradeOrderSide.SELL,
                locally_filled_amount=decimal.Decimal("0.3"),
                filled_price=decimal.Decimal("50000"),
                is_locked=True,
            )
            register_fill(hedging_engine, fill)
            
            # Get locked amounts
            locked_base, locked_quote = hedging_engine.get_locked_base_and_quote(SYMBOL)
            
            # SELL order locks quote (amount * price)
            assert locked_base == trading_constants.ZERO
            assert locked_quote == decimal.Decimal("15000")  # 0.3 * 50000

    async def test_aggregates_multiple_fills_same_symbol(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create multiple locked fills
            fill_1 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="buy_order_1",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.2"),
                is_locked=True,
            )
            fill_2 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="buy_order_2",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.3"),
                is_locked=True,
            )
            fill_3 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="sell_order_1",
                side=trading_enums.TradeOrderSide.SELL,
                locally_filled_amount=decimal.Decimal("0.1"),
                filled_price=decimal.Decimal("50000"),
                is_locked=True,
            )
            register_fill(hedging_engine, fill_1)
            register_fill(hedging_engine, fill_2)
            register_fill(hedging_engine, fill_3)
            
            # Get locked amounts
            locked_base, locked_quote = hedging_engine.get_locked_base_and_quote(SYMBOL)
            
            # Should aggregate: base = 0.2 + 0.3 = 0.5, quote = 0.1 * 50000 = 5000
            assert locked_base == decimal.Decimal("0.5")
            assert locked_quote == decimal.Decimal("5000")

    async def test_ignores_unlocked_fills(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create locked and unlocked fills
            locked_fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="buy_order_locked",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.5"),
                is_locked=True,
            )
            unlocked_fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="buy_order_unlocked",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.3"),
                is_locked=False,
            )
            register_fill(hedging_engine, locked_fill)
            register_fill(hedging_engine, unlocked_fill)
            
            # Get locked amounts
            locked_base, locked_quote = hedging_engine.get_locked_base_and_quote(SYMBOL)
            
            # Should only count locked fill
            assert locked_base == decimal.Decimal("0.5")
            assert locked_quote == trading_constants.ZERO

    async def test_aggregates_across_symbols_sharing_base(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register symbols sharing BTC base
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                hedging_engine.register_symbol(
                    symbol="BTC/EUR",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                
                # Create fills for both symbols
                fill_btc_usdt = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="btc_usdt_order",
                    symbol="BTC/USDT",
                    side=trading_enums.TradeOrderSide.BUY,
                    locally_filled_amount=decimal.Decimal("0.2"),
                    is_locked=True,
                )
                fill_btc_eur = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="btc_eur_order",
                    symbol="BTC/EUR",
                    side=trading_enums.TradeOrderSide.BUY,
                    locally_filled_amount=decimal.Decimal("0.3"),
                    is_locked=True,
                )
                register_fill(hedging_engine, fill_btc_usdt)
                register_fill(hedging_engine, fill_btc_eur)
                
                # Query for BTC/USDT (should aggregate base from both symbols)
                locked_base, locked_quote = hedging_engine.get_locked_base_and_quote("BTC/USDT")
                
                # Should aggregate base from both: 0.2 + 0.3 = 0.5
                assert locked_base == decimal.Decimal("0.5")
                assert locked_quote == trading_constants.ZERO

    async def test_aggregates_across_symbols_sharing_quote(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register symbols sharing USDT quote
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                hedging_engine.register_symbol(
                    symbol="ETH/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                
                # Create SELL fills for both symbols (locks quote)
                fill_btc_usdt = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="btc_usdt_sell",
                    symbol="BTC/USDT",
                    side=trading_enums.TradeOrderSide.SELL,
                    locally_filled_amount=decimal.Decimal("0.1"),
                    filled_price=decimal.Decimal("50000"),
                    is_locked=True,
                )
                fill_eth_usdt = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="eth_usdt_sell",
                    symbol="ETH/USDT",
                    side=trading_enums.TradeOrderSide.SELL,
                    locally_filled_amount=decimal.Decimal("0.2"),
                    filled_price=decimal.Decimal("3000"),
                    is_locked=True,
                )
                register_fill(hedging_engine, fill_btc_usdt)
                register_fill(hedging_engine, fill_eth_usdt)
                
                # Query for BTC/USDT (should aggregate quote from both symbols)
                locked_base, locked_quote = hedging_engine.get_locked_base_and_quote("BTC/USDT")
                
                # Should aggregate quote from both: 0.1 * 50000 + 0.2 * 3000 = 5000 + 600 = 5600
                assert locked_base == trading_constants.ZERO
                assert locked_quote == decimal.Decimal("5600")

    async def test_handles_mixed_base_and_quote_matches(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register BTC/USDT
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                
                # Create BUY fill (locks base) and SELL fill (locks quote)
                fill_buy = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="btc_buy",
                    symbol="BTC/USDT",
                    side=trading_enums.TradeOrderSide.BUY,
                    locally_filled_amount=decimal.Decimal("0.2"),
                    is_locked=True,
                )
                fill_sell = create_hedging_fill(
                    trading_exchange_manager=hedging_engine._trading_exchange_manager,
                    order_exchange_id="btc_sell",
                    symbol="BTC/USDT",
                    side=trading_enums.TradeOrderSide.SELL,
                    locally_filled_amount=decimal.Decimal("0.1"),
                    filled_price=decimal.Decimal("50000"),
                    is_locked=True,
                )
                register_fill(hedging_engine, fill_buy)
                register_fill(hedging_engine, fill_sell)
                
                # Query for BTC/USDT
                locked_base, locked_quote = hedging_engine.get_locked_base_and_quote("BTC/USDT")
                
                # Should have both base and quote locked
                assert locked_base == decimal.Decimal("0.2")
                assert locked_quote == decimal.Decimal("5000")  # 0.1 * 50000

    async def test_returns_zero_for_unmatched_symbol(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create fill for BTC/USDT
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="btc_order",
                symbol="BTC/USDT",
                is_locked=True,
            )
            register_fill(hedging_engine, fill)
            
            # Query for unrelated symbol (e.g., ETH/EUR)
            # This should return zero since no hedging symbols match
            locked_base, locked_quote = hedging_engine.get_locked_base_and_quote("ETH/EUR")
            
            assert locked_base == trading_constants.ZERO
            assert locked_quote == trading_constants.ZERO

    async def test_handles_partial_fills_for_same_order(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create multiple partial fills for the same order
            fill_1 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="partial_order_123",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.1"),
                is_locked=True,
            )
            fill_2 = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="partial_order_123",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.15"),
                is_locked=True,
            )
            register_fill(hedging_engine, fill_1)
            register_fill(hedging_engine, fill_2)
            
            # Get locked amounts
            locked_base, locked_quote = hedging_engine.get_locked_base_and_quote(SYMBOL)
            
            # Should aggregate both partial fills
            assert locked_base == decimal.Decimal("0.25")  # 0.1 + 0.15
            assert locked_quote == trading_constants.ZERO


class TestOnNewPrice:
    """Test class for on_new_price method."""

    async def test_updates_last_hedging_price(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            initial_price = details.last_hedging_price
            
            # Update price
            new_price = decimal.Decimal("51000")
            await hedging_engine.on_new_price(SYMBOL, new_price)
            
            # Verify price was updated
            assert details.last_hedging_price == new_price
            assert details.last_hedging_price != initial_price

    async def test_calls_volatility_threshold_checker_on_new_price(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            volatility_threshold_checker = details.volatility_threshold_checker
            
            # Mock on_new_price to verify it's called
            with mock.patch.object(volatility_threshold_checker, "on_new_price", return_value=(False, None)) as mock_on_new_price:
                new_price = decimal.Decimal("51000")
                await hedging_engine.on_new_price(SYMBOL, new_price)
            
            # Verify volatility_threshold_checker.on_new_price was called
            mock_on_new_price.assert_called_once_with(new_price)

    async def test_raises_error_when_volatility_met(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            volatility_threshold_checker = details.volatility_threshold_checker
            
            # Mock volatility threshold checker to return threshold met
            with mock.patch.object(volatility_threshold_checker, "on_new_price", return_value=(True, "Test reason")):
                new_price = decimal.Decimal("51000")
                
                # Should raise HedgingEngineReachedMaxToleratedVolatility
                with pytest.raises(hedging_errors.HedgingEngineReachedMaxToleratedVolatility):
                    await hedging_engine.on_new_price(SYMBOL, new_price)
            
            # Verify state was updated to MAX_VOLATILITY_REACHED
            assert details.state == hedging_engine_import.HedgingEngineState.MAX_VOLATILITY_REACHED

    async def test_resumes_hedging_when_volatility_no_longer_met(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            volatility_threshold_checker = details.volatility_threshold_checker
            
            # Set state to MAX_VOLATILITY_REACHED
            details.state = hedging_engine_import.HedgingEngineState.MAX_VOLATILITY_REACHED
            
            # Mock volatility threshold checker to return not met (volatility has passed)
            with mock.patch.object(volatility_threshold_checker, "on_new_price", return_value=(False, None)), \
                 mock.patch.object(hedging_engine._logger, "info") as mock_info:
                new_price = decimal.Decimal("51000")
                await hedging_engine.on_new_price(SYMBOL, new_price)
            
            # Verify state was resumed to HEDGING
            assert details.state == hedging_engine_import.HedgingEngineState.HEDGING
            
            # Verify resume message was logged
            mock_info.assert_called_once()
            log_message = mock_info.call_args[0][0]
            assert "Resuming hedging" in log_message
            assert SYMBOL in log_message

    async def test_does_not_resume_when_volatility_still_met(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            volatility_threshold_checker = details.volatility_threshold_checker
            
            # Set state to MAX_VOLATILITY_REACHED
            details.state = hedging_engine_import.HedgingEngineState.MAX_VOLATILITY_REACHED
            
            # Mock volatility threshold checker to still return threshold met
            with mock.patch.object(volatility_threshold_checker, "on_new_price", return_value=(True, "Test reason")):
                new_price = decimal.Decimal("51000")
                
                # Should raise error (not resume)
                with pytest.raises(hedging_errors.HedgingEngineReachedMaxToleratedVolatility):
                    await hedging_engine.on_new_price(SYMBOL, new_price)
            
            # Verify state remains MAX_VOLATILITY_REACHED
            assert details.state == hedging_engine_import.HedgingEngineState.MAX_VOLATILITY_REACHED

    async def test_handles_multiple_symbols_independently(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register two symbols
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                hedging_engine.register_symbol(
                    symbol="ETH/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                
                details_btc = hedging_engine.get_symbol_details("BTC/USDT")
                details_eth = hedging_engine.get_symbol_details("ETH/USDT")
                
                # Update price for BTC
                await hedging_engine.on_new_price("BTC/USDT", decimal.Decimal("50000"))
                
                # Update price for ETH
                await hedging_engine.on_new_price("ETH/USDT", decimal.Decimal("3000"))
                
                # Verify each symbol's price was updated independently
                assert details_btc.last_hedging_price == decimal.Decimal("50000")
                assert details_eth.last_hedging_price == decimal.Decimal("3000")

    async def test_updates_price_even_when_volatility_check_fails(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            volatility_threshold_checker = details.volatility_threshold_checker
            
            # Mock volatility threshold checker to return threshold met (will raise error)
            with mock.patch.object(volatility_threshold_checker, "on_new_price", return_value=(True, "Test reason")):
                new_price = decimal.Decimal("51000")
                
                # Should raise error, but price should still be updated before the error
                try:
                    await hedging_engine.on_new_price(SYMBOL, new_price)
                except hedging_errors.HedgingEngineReachedMaxToleratedVolatility:
                    pass
                
                # Verify price was updated even though error was raised
                assert details.last_hedging_price == new_price


class TestAsyncStartForHedgingDetails:
    """Test class for _async_start_for_hedging_details method."""

    async def test_successful_initialization_sets_state_to_hedging(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock the abstract method to return sufficient funds
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("10"), decimal.Decimal("1000"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify state is set to HEDGING
            assert details.state == hedging_engine_import.HedgingEngineState.HEDGING
            # Verify initialization event is set
            assert details.completed_initialization.is_set()

    async def test_sets_initialization_event_on_success(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Verify event is not set initially
            assert not details.completed_initialization.is_set()
            
            # Mock successful initialization
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("10"), decimal.Decimal("1000"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify event is set
            assert details.completed_initialization.is_set()

    async def test_sets_initialization_event_on_failure(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock missing hedging funds error
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("0.1"), decimal.Decimal("10"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify event is still set even on failure
            assert details.completed_initialization.is_set()

    async def test_sets_state_to_initialization_failed_on_missing_funds(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock insufficient hedging funds (less than trading budget)
            # Trading budget will be at least max_base_budget=1 and max_quote_budget=100
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("0.1"), decimal.Decimal("10"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify state is set to MISSING_HEDGING_FUNDS
            assert details.state == hedging_engine_import.HedgingEngineState.MISSING_HEDGING_FUNDS

    async def test_sets_state_to_initialization_failed_on_other_errors(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock an unexpected error
            test_error = ValueError("Unexpected error")
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", side_effect=test_error), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()), \
                 mock.patch.object(hedging_engine._logger, "exception") as mock_exception:
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify state is set to MISSING_HEDGING_FUNDS
            assert details.state == hedging_engine_import.HedgingEngineState.INITIALIZATION_FAILED
            # Verify error was logged
            mock_exception.assert_called_once()

    async def test_calls_wait_for_dependencies(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock wait_for_dependencies_if_required
            with mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required") as mock_wait, \
                 mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("10"), decimal.Decimal("1000"))):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify wait_for_dependencies_if_required was called
            mock_wait.assert_called_once()

    async def test_logs_start_message(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock successful initialization
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("10"), decimal.Decimal("1000"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()), \
                 mock.patch.object(hedging_engine._logger, "info") as mock_info:
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify start message was logged
            mock_info.assert_called()
            log_calls = [call[0][0] for call in mock_info.call_args_list]
            start_message = next((msg for msg in log_calls if "Hedging engine starting" in msg), None)
            assert start_message is not None
            assert hedging_engine._trading_exchange_manager.exchange_name in start_message
            assert hedging_engine._hedging_exchange_manager.exchange_name in start_message
            assert str(details.symbol) in start_message

    async def test_logs_error_on_failure(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock an error
            test_error = RuntimeError("Test error")
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", side_effect=test_error), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()), \
                 mock.patch.object(hedging_engine._logger, "exception") as mock_exception:
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify error was logged
            mock_exception.assert_called_once()
            # Check that the error message contains the error
            call_args = mock_exception.call_args
            assert test_error in call_args[0] or str(test_error) in str(call_args)

    async def test_handles_sufficient_hedging_funds(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock sufficient hedging funds (more than trading budget)
            # Trading budget will be limited by max_base_budget=1 and max_quote_budget=100
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("10"), decimal.Decimal("1000"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify successful initialization
            assert details.state == hedging_engine_import.HedgingEngineState.HEDGING
            assert details.completed_initialization.is_set()

    async def test_handles_insufficient_base_funds(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock insufficient base funds (but sufficient quote)
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("0.1"), decimal.Decimal("1000"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify initialization failed
            assert details.state == hedging_engine_import.HedgingEngineState.MISSING_HEDGING_FUNDS

    async def test_handles_insufficient_quote_funds(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            details = hedging_engine.get_symbol_details(SYMBOL)
            
            # Mock insufficient quote funds (but sufficient base)
            with mock.patch.object(hedging_engine, "_get_base_and_quote_hedging_budget", return_value=(decimal.Decimal("10"), decimal.Decimal("10"))), \
                 mock.patch.object(hedging_engine, "_wait_for_dependencies_if_required", mock.AsyncMock()):
                await hedging_engine._async_start_for_hedging_details(details)
            
            # Verify initialization failed
            assert details.state == hedging_engine_import.HedgingEngineState.MISSING_HEDGING_FUNDS


class TestStop:
    """Test class for stop method."""

    async def test_cancels_pending_start_tasks(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, mock_async_start_for_hedging_details=False) as hedging_engine:
            # Create a pending task
            async def dummy_task():
                await asyncio.sleep(10)
            
            task = asyncio.create_task(dummy_task())
            hedging_engine._start_tasks.append(task)
            
            # Stop the engine
            await hedging_engine.stop()
            
            await asyncio_tools.wait_asyncio_next_cycle()
            # Verify task was cancelled
            assert task.cancelled()
            # Verify start_tasks is cleared
            assert len(hedging_engine._start_tasks) == 0

    async def test_handles_multiple_symbols(self, order_book_distribution):
        async with hedging_engine_context() as hedging_engine:
            hedging_engine._hedging_exchange_manager = hedging_engine._trading_exchange_manager
            with mock.patch.object(hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
                # Register multiple symbols
                hedging_engine.register_symbol(
                    symbol="BTC/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
                hedging_engine.register_symbol(
                    symbol="ETH/USDT",
                    hedging_profit_threshold=decimal.Decimal("0.01"),
                    hedging_max_loss_threshold=decimal.Decimal("0.01"),
                    order_book_distribution=order_book_distribution,
                    max_positive_percent_price_change=40,
                    max_negative_percent_price_change=12,
                    average_price_counted_minutes=10,
                )
            
            details_btc = hedging_engine.get_symbol_details("BTC/USDT")
            details_eth = hedging_engine.get_symbol_details("ETH/USDT")
            
            # Add fills to both
            fill_btc = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="btc_order",
                symbol="BTC/USDT",
                is_locked=True,
            )
            fill_eth = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="eth_order",
                symbol="ETH/USDT",
                is_locked=True,
            )
            register_fill(hedging_engine, fill_btc)
            register_fill(hedging_engine, fill_eth)
            
            # Mock consumers
            hedging_engine._consumers = [mock.AsyncMock()]
            
            # Stop the engine
            await hedging_engine.stop()
            
            # Verify both symbols were stopped
            assert details_btc.state == hedging_engine_import.HedgingEngineState.STOPPED
            assert details_eth.state == hedging_engine_import.HedgingEngineState.STOPPED
            assert len(details_btc.hedging_fills_by_order_id) == 0
            assert len(details_eth.hedging_fills_by_order_id) == 0
            # Verify all details were removed
            assert len(hedging_engine._hedging_details_by_symbol) == 0


class TestGetHedgingOrderFee:
    """Test class for get_hedging_order_fee method."""

    async def test_returns_fee_when_is_from_exchange_true(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a fill
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="order_123",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.1"),
            )
            
            # Create filled hedging order with fee from exchange
            filled_hedging_order = {
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "1025",
                trading_enums.ExchangeConstantsOrderColumns.FEE.value: {
                    trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                    trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.5"),
                    trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
                },
            }
            
            # Get hedging order fee
            # Should return fee as-is and not be estimated
            assert fill.get_hedging_order_fee(
                hedging_engine._hedging_exchange_manager,
                filled_hedging_order
            ) == (
                {
                    trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                    trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.5"),
                    trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
                },
                False
            )

    async def test_estimates_fee_when_is_from_exchange_false(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a fill
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="order_123",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.1"),
            )
            
            # Create filled hedging order with fee not from exchange
            filled_hedging_order = {
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "1025",
                trading_enums.ExchangeConstantsOrderColumns.FEE.value: {
                    trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                    trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.5"),
                    trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: False,
                },
            }
            
            # Mock get_trade_fee
            mock_fee = {
                trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1025"),
            }
            with mock.patch.object(
                hedging_engine._hedging_exchange_manager.exchange,
                "get_trade_fee",
                return_value=mock_fee
            ) as mock_get_trade_fee:
                # Get hedging order fee
                # Should estimate fee and return True for is_estimated
                assert fill.get_hedging_order_fee(
                    hedging_engine._hedging_exchange_manager,
                    filled_hedging_order
                ) == (
                    {
                        trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                        trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1025"),
                    },
                    True
                )
                
                # Verify get_trade_fee was called with correct parameters
                mock_get_trade_fee.assert_called_once_with(
                    fill.fill_trade.symbol,
                    trading_enums.TraderOrderType.SELL_MARKET,
                    fill.fill_trade.executed_quantity,
                    decimal.Decimal("1025"),
                    trading_enums.ExchangeConstantsOrderColumns.TAKER.value
                )

    async def test_estimates_fee_when_fee_missing(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create a fill
            fill = create_hedging_fill(
                trading_exchange_manager=hedging_engine._trading_exchange_manager,
                order_exchange_id="order_123",
                side=trading_enums.TradeOrderSide.BUY,
                locally_filled_amount=decimal.Decimal("0.1"),
            )
            
            # Create filled hedging order without fee
            filled_hedging_order = {
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: "1025",
            }
            
            # Mock get_trade_fee
            mock_fee = {
                trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1025"),
            }
            with mock.patch.object(
                hedging_engine._hedging_exchange_manager.exchange,
                "get_trade_fee",
                return_value=mock_fee
            ) as mock_get_trade_fee:
                # Get hedging order fee
                # Should estimate fee and return True for is_estimated
                assert fill.get_hedging_order_fee(
                    hedging_engine._hedging_exchange_manager,
                    filled_hedging_order
                ) == (
                    {
                        trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                        trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1025"),
                    },
                    True
                )
                
                # Verify get_trade_fee was called
                mock_get_trade_fee.assert_called_once()


class TestFillTradeFactory:
    """Test class for fill_trade_factory static method."""

    async def test_returns_duplicate_when_matching_trade_exists(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create an existing trade in trades_manager
            existing_trade = octobot_trading.personal_data.create_trade_from_dict(
                hedging_engine._trading_exchange_manager.trader,
                {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                    trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),
                    trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: decimal.Decimal("0.1"),
                    trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: 1234567890.0,
                    trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
                    trading_enums.ExchangeConstantsOrderColumns.COST.value: decimal.Decimal("100"),
                    trading_enums.ExchangeConstantsOrderColumns.FEE.value: {
                        trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                        trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1"),
                    },
                }
            )
            
            # Mock trades_manager.get_trades to return the existing trade
            hedging_engine._trading_exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
                return_value=[existing_trade]
            )
            
            # Create order dict matching the existing trade
            order = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),
            }
            
            # Call fill_trade_factory
            result_trade = hedging_engine_import.HedgingEngine.fill_trade_factory(
                hedging_engine._trading_exchange_manager,
                order,
                decimal.Decimal("0.1"),
                1234567890.0,
            )
            
            # Should return a duplicate of the existing trade
            assert result_trade is not existing_trade  # Different object
            assert result_trade.exchange_manager is hedging_engine._trading_exchange_manager
            assert result_trade.exchange_order_id == existing_trade.exchange_order_id
            assert result_trade.symbol == existing_trade.symbol
            assert result_trade.side == existing_trade.side
            assert result_trade.executed_price == existing_trade.executed_price
            assert result_trade.executed_quantity == existing_trade.executed_quantity
            assert result_trade.fee == existing_trade.fee # reported fee from found trade
            assert result_trade.taker_or_maker == trading_enums.ExchangeConstantsOrderColumns.MAKER.value

    async def test_creates_new_trade_when_no_matching_trade_exists(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Mock trades_manager.get_trades to return empty list
            hedging_engine._trading_exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
                return_value=[]
            )
            
            # Create order dict
            order = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_456",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.SELL,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("2000"),
            }
            
            locally_filled_amount = decimal.Decimal("0.2")
            filled_time = 1234567891.0
            
            # Call fill_trade_factory
            result_trade = hedging_engine_import.HedgingEngine.fill_trade_factory(
                hedging_engine._trading_exchange_manager,
                order,
                locally_filled_amount,
                filled_time,
            )
            
            # Should create a new trade with correct properties
            assert result_trade.exchange_manager is hedging_engine._trading_exchange_manager
            assert result_trade.exchange_order_id == "order_456"
            assert result_trade.symbol == SYMBOL
            assert result_trade.side == trading_enums.TradeOrderSide.SELL
            assert result_trade.executed_price == decimal.Decimal("2000")
            assert result_trade.executed_quantity == locally_filled_amount
            assert result_trade.executed_time == filled_time
            assert result_trade.total_cost == locally_filled_amount * decimal.Decimal("2000")
            assert result_trade.taker_or_maker == trading_enums.ExchangeConstantsOrderColumns.MAKER.value

    async def test_skips_trade_with_different_amount(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create an existing trade with different amount
            existing_trade = octobot_trading.personal_data.create_trade_from_dict(
                hedging_engine._trading_exchange_manager.trader,
                {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                    trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),
                    trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: decimal.Decimal("0.2"),  # Different amount
                    trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: 1234567890.0,
                    trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
                    trading_enums.ExchangeConstantsOrderColumns.COST.value: decimal.Decimal("200"),
                    trading_enums.ExchangeConstantsOrderColumns.FEE.value: {
                        trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                        trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1"),
                    },
                }
            )
            
            # Mock trades_manager.get_trades to return the existing trade
            hedging_engine._trading_exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
                return_value=[existing_trade]
            )
            
            # Create order dict with different amount
            order = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),
            }
            
            # Call fill_trade_factory with different amount
            result_trade = hedging_engine_import.HedgingEngine.fill_trade_factory(
                hedging_engine._trading_exchange_manager,
                order,
                decimal.Decimal("0.1"),  # Different from existing trade
                1234567890.0,
            )
            
            # Should create a new trade (not duplicate) because amounts don't match
            assert result_trade is not existing_trade
            assert result_trade.exchange_manager is hedging_engine._trading_exchange_manager
            assert result_trade.executed_quantity == decimal.Decimal("0.1")  # Should use the requested amount
            # did not report fee from found trade
            assert result_trade.fee is None
            assert result_trade.taker_or_maker == trading_enums.ExchangeConstantsOrderColumns.MAKER.value

    async def test_skips_trade_with_different_price(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create an existing trade with different price
            existing_trade = octobot_trading.personal_data.create_trade_from_dict(
                hedging_engine._trading_exchange_manager.trader,
                {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                    trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1500"),  # Different price
                    trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: decimal.Decimal("0.1"),
                    trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: 1234567890.0,
                    trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
                    trading_enums.ExchangeConstantsOrderColumns.COST.value: decimal.Decimal("150"),
                    trading_enums.ExchangeConstantsOrderColumns.FEE.value: {
                        trading_enums.FeePropertyColumns.CURRENCY.value: "USDT",
                        trading_enums.FeePropertyColumns.COST.value: decimal.Decimal("0.1"),
                    },
                }
            )
            
            # Mock trades_manager.get_trades to return the existing trade
            hedging_engine._trading_exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
                return_value=[existing_trade]
            )
            
            # Create order dict with different price
            order = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),  # Different price
            }
            
            # Call fill_trade_factory with different price
            result_trade = hedging_engine_import.HedgingEngine.fill_trade_factory(
                hedging_engine._trading_exchange_manager,
                order,
                decimal.Decimal("0.1"),
                1234567890.0,
            )
            
            # Should create a new trade (not duplicate) because prices don't match
            assert result_trade is not existing_trade
            assert result_trade.executed_price == decimal.Decimal("1000")  # Should use the requested price
            # did not report fee from found trade
            assert result_trade.fee is None
            assert result_trade.taker_or_maker == trading_enums.ExchangeConstantsOrderColumns.MAKER.value

    async def test_selects_correct_trade_from_multiple_trades(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Create multiple trades with same order_id but different amounts/prices
            trade_1 = octobot_trading.personal_data.create_trade_from_dict(
                hedging_engine._trading_exchange_manager.trader,
                {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                    trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),
                    trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: decimal.Decimal("0.1"),
                    trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: 1234567890.0,
                    trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
                    trading_enums.ExchangeConstantsOrderColumns.COST.value: decimal.Decimal("100"),
                }
            )
            
            trade_2 = octobot_trading.personal_data.create_trade_from_dict(
                hedging_engine._trading_exchange_manager.trader,
                {
                    trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                    trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                    trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                    trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),
                    trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: decimal.Decimal("0.2"),  # Different amount
                    trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: 1234567891.0,
                    trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
                    trading_enums.ExchangeConstantsOrderColumns.COST.value: decimal.Decimal("200"),
                }
            )
            
            # Mock trades_manager.get_trades to return both trades
            hedging_engine._trading_exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
                return_value=[trade_1, trade_2]
            )
            
            # Create order dict matching trade_1
            order = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_123",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: SYMBOL,
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("1000"),
            }
            
            # Call fill_trade_factory with amount matching trade_1
            result_trade = hedging_engine_import.HedgingEngine.fill_trade_factory(
                hedging_engine._trading_exchange_manager,
                order,
                decimal.Decimal("0.1"),  # Matches trade_1
                1234567890.0,
            )
            
            # Should return duplicate of trade_1 (the matching one)
            assert result_trade is not trade_1  # Different object
            assert result_trade.executed_quantity == trade_1.executed_quantity
            assert result_trade.executed_price == trade_1.executed_price
            assert result_trade.executed_quantity != trade_2.executed_quantity  # Should not match trade_2
            assert result_trade.taker_or_maker == trading_enums.ExchangeConstantsOrderColumns.MAKER.value

    async def test_handles_empty_trades_manager(self, order_book_distribution):
        async with hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as hedging_engine:
            # Mock trades_manager.get_trades to return empty list
            hedging_engine._trading_exchange_manager.exchange_personal_data.trades_manager.get_trades = mock.Mock(
                return_value=[]
            )
            
            # Create order dict
            order = {
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: "order_789",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "ETH/USDT",
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: trading_enums.TradeOrderSide.BUY,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: decimal.Decimal("3000"),
            }
            
            locally_filled_amount = decimal.Decimal("0.5")
            filled_time = 1234567892.0
            
            # Call fill_trade_factory
            result_trade = hedging_engine_import.HedgingEngine.fill_trade_factory(
                hedging_engine._trading_exchange_manager,
                order,
                locally_filled_amount,
                filled_time,
            )
            
            # Should create a new trade
            assert result_trade.exchange_order_id == "order_789"
            assert result_trade.symbol == "ETH/USDT"
            assert result_trade.executed_quantity == locally_filled_amount
            assert result_trade.executed_price == decimal.Decimal("3000")
            assert result_trade.executed_time == filled_time
            assert result_trade.taker_or_maker == trading_enums.ExchangeConstantsOrderColumns.MAKER.value