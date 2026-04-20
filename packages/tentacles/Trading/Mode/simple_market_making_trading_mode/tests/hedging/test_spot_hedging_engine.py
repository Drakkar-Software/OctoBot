import pytest
import mock
import decimal
import contextlib

import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.spot_hedging_engine as spot_hedging_engine_import
import octobot_trading.api as trading_api
import octobot_trading.exchanges
import octobot_trading.personal_data
import octobot_trading.personal_data.orders.groups.one_cancels_the_other_order_group as oco_group
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.errors as hedging_errors

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
async def spot_hedging_engine_context():
    async with hedging_tests.exchange_manager_context() as exchange_manager:
        yield spot_hedging_engine_import.SpotHedgingEngine(
            trading_exchange_manager=exchange_manager,
            hedging_exchange_name="hedgex",
        )


@contextlib.asynccontextmanager
async def spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution, symbol=SYMBOL, mock_async_start_for_hedging_details=True):
    async with spot_hedging_engine_context() as spot_hedging_engine:
        # use the same exchange manager to simplify testing
        spot_hedging_engine._hedging_exchange_manager = spot_hedging_engine._trading_exchange_manager
        with mock.patch.object(spot_hedging_engine, "_async_start_for_hedging_details", mock.AsyncMock()):
            spot_hedging_engine.register_symbol(
                symbol=symbol,
                hedging_profit_threshold=decimal.Decimal("0.01"),
                hedging_max_loss_threshold=decimal.Decimal("0.01"),
                order_book_distribution=order_book_distribution,
                max_positive_percent_price_change=40,
                max_negative_percent_price_change=12,
                average_price_counted_minutes=10,
            )
            if mock_async_start_for_hedging_details:
                yield spot_hedging_engine
        if not mock_async_start_for_hedging_details:
            yield spot_hedging_engine


async def test__init__():
    async with spot_hedging_engine_context() as spot_hedging_engine:
        assert isinstance(spot_hedging_engine._trading_exchange_manager, octobot_trading.exchanges.ExchangeManager)
        assert spot_hedging_engine.hedging_exchange_name == "hedgex"
        assert spot_hedging_engine._consumers == []
        assert spot_hedging_engine._hedging_details_by_symbol == {}
        assert spot_hedging_engine._logger is not None
        assert spot_hedging_engine._active_order_swap_timeout == spot_hedging_engine_import.DEFAULT_ACTIVE_ORDER_SWAP_TIMEOUT


async def test_get_base_and_quote_hedging_budget(order_book_distribution):
    async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
        details = spot_hedging_engine.get_symbol_details(SYMBOL)
        base_available_holding = trading_api.get_portfolio_currency(spot_hedging_engine._hedging_exchange_manager, details.symbol.base).available
        quote_available_holding = trading_api.get_portfolio_currency(spot_hedging_engine._hedging_exchange_manager, details.symbol.quote).available
        assert base_available_holding > trading_constants.ZERO
        assert quote_available_holding > trading_constants.ZERO
        assert spot_hedging_engine._get_base_and_quote_hedging_budget(details) == (base_available_holding, quote_available_holding)


class TestCreateHedgingOrder:
    """Test class for _create_hedging_order method."""

    async def test_creates_hedging_order_for_buy_fill(self, order_book_distribution):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            # Create a BUY fill
            fill = create_hedging_fill(
                trading_exchange_manager=spot_hedging_engine._trading_exchange_manager,
                order_exchange_id="order_123",
                side=trading_enums.TradeOrderSide.BUY,
                hedging_price=decimal.Decimal("50000"),
                locally_filled_amount=decimal.Decimal("0.1"),
            )
            
            # Create real hedging order
            hedging_order = create_hedging_order(
                spot_hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_123",
            )
            
            # Mock _create_maybe_oco_hedging_order
            with mock.patch.object(spot_hedging_engine, "_create_maybe_oco_hedging_order", mock.AsyncMock(return_value=hedging_order)) as mock_create_oco:
                result = await spot_hedging_engine._create_hedging_order(fill)
            
            # Verify result
            assert result is hedging_order
            
            # Verify _create_maybe_oco_hedging_order was called with correct parameters
            details = spot_hedging_engine.get_symbol_details(fill.fill_trade.symbol)
            expected_stop_price = fill.hedging_price * (1 - details.hedging_max_loss_threshold / trading_constants.ONE_HUNDRED)
            mock_create_oco.assert_awaited_once_with(
                fill.fill_trade.symbol,
                trading_enums.TradeOrderSide.SELL,
                fill.fill_trade.executed_quantity,
                fill.hedging_price,
                expected_stop_price,
            )

    async def test_creates_hedging_order_for_sell_fill(self, order_book_distribution):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            # Create a SELL fill
            fill = create_hedging_fill(
                trading_exchange_manager=spot_hedging_engine._trading_exchange_manager,
                order_exchange_id="order_456",
                side=trading_enums.TradeOrderSide.SELL,
                hedging_price=decimal.Decimal("51000"),
                locally_filled_amount=decimal.Decimal("0.2"),
            )
            
            # Create real hedging order
            hedging_order = create_hedging_order(
                spot_hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_456",
            )
            
            # Mock _create_maybe_oco_hedging_order
            with mock.patch.object(spot_hedging_engine, "_create_maybe_oco_hedging_order", mock.AsyncMock(return_value=hedging_order)) as mock_create_oco:
                result = await spot_hedging_engine._create_hedging_order(fill)
            
            # Verify result
            assert result is hedging_order
            
            # Verify _create_maybe_oco_hedging_order was called with correct parameters
            details = spot_hedging_engine.get_symbol_details(fill.fill_trade.symbol)
            expected_stop_price = fill.hedging_price * (1 + details.hedging_max_loss_threshold / trading_constants.ONE_HUNDRED)
            mock_create_oco.assert_awaited_once_with(
                fill.fill_trade.symbol,
                trading_enums.TradeOrderSide.BUY,
                fill.fill_trade.executed_quantity,
                fill.hedging_price,
                expected_stop_price,
            )

    async def test_raises_error_when_oco_order_creation_returns_none(self, order_book_distribution):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            fill = create_hedging_fill(
                trading_exchange_manager=spot_hedging_engine._trading_exchange_manager,
                order_exchange_id="order_202",
                hedging_price=decimal.Decimal("50000"),
            )
            
            # Mock _create_maybe_oco_hedging_order to return None
            with mock.patch.object(spot_hedging_engine, "_create_maybe_oco_hedging_order", mock.AsyncMock(return_value=None)):
                with pytest.raises(hedging_errors.HedgingOrderCreationError) as exc_info:
                    await spot_hedging_engine._create_hedging_order(fill)
            
            # Verify error message contains relevant information
            error_message = str(exc_info.value)
            assert fill.fill_trade.symbol in error_message
            assert str(fill.hedging_price) in error_message
            assert "SELL" in error_message or "BUY" in error_message

    async def test_uses_correct_symbol_details(self, order_book_distribution):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            fill = create_hedging_fill(
                trading_exchange_manager=spot_hedging_engine._trading_exchange_manager,
                order_exchange_id="order_303",
                symbol="ETH/USDT",
            )
            
            # Register ETH/USDT symbol with different threshold
            spot_hedging_engine.register_symbol(
                symbol="ETH/USDT",
                hedging_profit_threshold=decimal.Decimal("0.02"),
                hedging_max_loss_threshold=decimal.Decimal("3.0"),  # Different threshold
                order_book_distribution=order_book_distribution,
                max_positive_percent_price_change=40,
                max_negative_percent_price_change=12,
                average_price_counted_minutes=10,
            )
            
            hedging_order = create_hedging_order(
                spot_hedging_engine._hedging_exchange_manager,
                exchange_order_id="hedge_order_303",
            )
            
            with mock.patch.object(spot_hedging_engine, "_create_maybe_oco_hedging_order", mock.AsyncMock(return_value=hedging_order)) as mock_create_oco:
                await spot_hedging_engine._create_hedging_order(fill)
            
            # Verify it uses the correct symbol details (ETH/USDT with 3.0% threshold)
            details = spot_hedging_engine.get_symbol_details("ETH/USDT")
            call_args = mock_create_oco.call_args
            expected_stop_price = fill.hedging_price * (1 - details.hedging_max_loss_threshold / trading_constants.ONE_HUNDRED)
            assert call_args[0][4] == expected_stop_price


    async def test_handles_different_hedging_max_loss_thresholds(self, order_book_distribution):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            details = spot_hedging_engine.get_symbol_details(SYMBOL)
            
            # Test with different thresholds
            test_cases = [
                (decimal.Decimal("0.5"), decimal.Decimal("50000")),  # 0.5% threshold
                (decimal.Decimal("5.0"), decimal.Decimal("50000")),   # 5.0% threshold
                (decimal.Decimal("10.0"), decimal.Decimal("50000")),  # 10.0% threshold
            ]
            
            for threshold, hedging_price in test_cases:
                details.hedging_max_loss_threshold = threshold
                fill = create_hedging_fill(
                    trading_exchange_manager=spot_hedging_engine._trading_exchange_manager,
                    order_exchange_id=f"order_{threshold}",
                    side=trading_enums.TradeOrderSide.BUY,
                    hedging_price=hedging_price,
                )
                
                hedging_order = create_hedging_order(
                    spot_hedging_engine._hedging_exchange_manager,
                    exchange_order_id=f"hedge_order_{threshold}",
                )
                
                with mock.patch.object(spot_hedging_engine, "_create_maybe_oco_hedging_order", mock.AsyncMock(return_value=hedging_order)) as mock_create_oco:
                    await spot_hedging_engine._create_hedging_order(fill)
                
                # Verify stop price calculation for each threshold
                call_args = mock_create_oco.call_args[0]
                expected_stop_price = hedging_price * (1 - threshold / trading_constants.ONE_HUNDRED)
                assert call_args[4] == expected_stop_price


class TestCreateMaybeOcoHedgingOrder:
    """Test class for _create_maybe_oco_hedging_order method."""

    async def test_raises_error_when_inactive_orders_not_enabled(self, order_book_distribution):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            # Disable inactive orders
            spot_hedging_engine._hedging_exchange_manager.trader.enable_inactive_orders = False
            
            with pytest.raises(hedging_errors.InactiveOrdersNotEnabledError) as exc_info:
                await spot_hedging_engine._create_maybe_oco_hedging_order(
                    symbol=SYMBOL,
                    heding_side=trading_enums.TradeOrderSide.BUY,
                    locally_filled_amount=decimal.Decimal("0.1"),
                    hedging_limit_price=decimal.Decimal("50000"),
                    stop_price=decimal.Decimal("51000"),
                )
            
            # Verify error message
            error_message = str(exc_info.value)
            assert "Inactive orders are not enabled" in error_message
            assert spot_hedging_engine._hedging_exchange_manager.exchange_name in error_message

    @pytest.mark.parametrize(
        "heding_side,expected_order_cls,expected_order_type",
        (
            (
                trading_enums.TradeOrderSide.BUY,
                octobot_trading.personal_data.BuyLimitOrder,
                trading_enums.TraderOrderType.BUY_LIMIT,
            ),
            (
                trading_enums.TradeOrderSide.SELL,
                octobot_trading.personal_data.SellLimitOrder,
                trading_enums.TraderOrderType.SELL_LIMIT,
            ),
        ),
    )
    async def test_creates_limit_only_without_stop_loss_when_stop_price_is_none(
        self,
        order_book_distribution,
        heding_side,
        expected_order_cls,
        expected_order_type,
    ):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(
            order_book_distribution
        ) as spot_hedging_engine:
            spot_hedging_engine._hedging_exchange_manager.trader.enable_inactive_orders = False

            symbol = SYMBOL
            locally_filled_amount = decimal.Decimal("0.01")
            hedging_limit_price = decimal.Decimal("50000")

            created_order = await spot_hedging_engine._create_maybe_oco_hedging_order(
                symbol=symbol,
                heding_side=heding_side,
                locally_filled_amount=locally_filled_amount,
                hedging_limit_price=hedging_limit_price,
                stop_price=None,
            )

            assert isinstance(created_order, expected_order_cls)
            assert created_order.order_type == expected_order_type
            assert created_order.order_group is None
            assert created_order.symbol == symbol
            assert created_order.origin_quantity == locally_filled_amount
            assert created_order.origin_price == hedging_limit_price

            open_orders = trading_api.get_open_orders(
                spot_hedging_engine._hedging_exchange_manager, symbol=symbol
            )
            assert not any(
                o.order_type == trading_enums.TraderOrderType.STOP_LOSS for o in open_orders
            )

    @pytest.mark.parametrize("is_self_managed", [True, False])
    async def test_creates_oco_order_for_buy_side(self, order_book_distribution, is_self_managed):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            with mock.patch.object(octobot_trading.personal_data.StopLossOrder, "is_self_managed", return_value=is_self_managed) as mock_is_self_managed:
                # Ensure inactive orders are enabled
                spot_hedging_engine._hedging_exchange_manager.trader.enable_inactive_orders = True
                
                symbol = SYMBOL
                heding_side = trading_enums.TradeOrderSide.BUY
                locally_filled_amount = decimal.Decimal("0.01")
                hedging_limit_price = decimal.Decimal("50000")
                stop_price = decimal.Decimal("51000")
                
                created_order = await spot_hedging_engine._create_maybe_oco_hedging_order(
                    symbol=symbol,
                    heding_side=heding_side,
                    locally_filled_amount=locally_filled_amount,
                    hedging_limit_price=hedging_limit_price,
                    stop_price=stop_price,
                )
                if is_self_managed:
                    mock_is_self_managed.assert_called_once()
                else:
                    assert mock_is_self_managed.call_count > 1
                
                # Verify order type is BUY_LIMIT for BUY side
                assert isinstance(created_order, octobot_trading.personal_data.BuyLimitOrder)
                assert created_order.order_type == trading_enums.TraderOrderType.BUY_LIMIT
                assert created_order.is_active is True
                if is_self_managed:
                    assert created_order.active_trigger is None
                else:
                    assert isinstance(created_order.active_trigger, octobot_trading.personal_data.PriceTrigger)
                    assert created_order.active_trigger.trigger_price == hedging_limit_price
                    assert created_order.active_trigger.trigger_above is False
                assert created_order.symbol == symbol
                assert created_order.origin_price == hedging_limit_price
                assert created_order.origin_quantity == locally_filled_amount
                assert isinstance(created_order.order_group, oco_group.OneCancelsTheOtherOrderGroup)
                group_orders = created_order.order_group.get_group_open_orders()
                assert len(group_orders) == 2
                assert created_order in group_orders
                assert isinstance(created_order.order_group.active_order_swap_strategy, octobot_trading.personal_data.TakeProfitFirstActiveOrderSwapStrategy)
                assert created_order.order_group.active_order_swap_strategy.swap_timeout == spot_hedging_engine._active_order_swap_timeout
                assert created_order.order_group.active_order_swap_strategy.trigger_price_configuration == trading_enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value

                # Verify stop order
                stop_order = [
                    order
                    for order in group_orders
                    if order.order_type == trading_enums.TraderOrderType.STOP_LOSS
                ][0]
                assert isinstance(stop_order, octobot_trading.personal_data.StopLossOrder)
                if is_self_managed:
                    assert stop_order.is_active is True
                    assert stop_order.active_trigger is None
                else:
                    assert stop_order.is_active is False
                    assert isinstance(stop_order.active_trigger, octobot_trading.personal_data.PriceTrigger)
                    assert stop_order.active_trigger.trigger_price == stop_price
                    assert stop_order.active_trigger.trigger_above is True
                assert stop_order.side == trading_enums.TradeOrderSide.BUY
                assert stop_order.symbol == symbol
                assert stop_order.origin_price == stop_price
                assert stop_order.origin_quantity == locally_filled_amount
                assert stop_order.order_group is created_order.order_group

    @pytest.mark.parametrize("is_self_managed", [True, False])
    async def test_creates_oco_order_for_sell_side(self, order_book_distribution, is_self_managed):
        async with spot_hedging_engine_with_registered_symbol_context_and_heding_exchange(order_book_distribution) as spot_hedging_engine:
            with mock.patch.object(octobot_trading.personal_data.StopLossOrder, "is_self_managed", return_value=is_self_managed) as mock_is_self_managed:
                # Ensure inactive orders are enabled
                spot_hedging_engine._hedging_exchange_manager.trader.enable_inactive_orders = True
                
                symbol = SYMBOL
                heding_side = trading_enums.TradeOrderSide.SELL
                locally_filled_amount = decimal.Decimal("0.2")
                hedging_limit_price = decimal.Decimal("51000")
                stop_price = decimal.Decimal("50000")

                created_order = await spot_hedging_engine._create_maybe_oco_hedging_order(
                    symbol=symbol,
                    heding_side=heding_side,
                    locally_filled_amount=locally_filled_amount,
                    hedging_limit_price=hedging_limit_price,
                    stop_price=stop_price,
                )
                if is_self_managed:
                    mock_is_self_managed.assert_called_once()
                else:
                    assert mock_is_self_managed.call_count > 1
                # Verify order type is SELL_LIMIT for SELL side
                assert isinstance(created_order, octobot_trading.personal_data.SellLimitOrder)
                assert created_order.order_type == trading_enums.TraderOrderType.SELL_LIMIT
                assert created_order.is_active is True
                if is_self_managed:
                    assert created_order.active_trigger is None
                else:
                    assert isinstance(created_order.active_trigger, octobot_trading.personal_data.PriceTrigger)
                    assert created_order.active_trigger.trigger_price == hedging_limit_price
                    assert created_order.active_trigger.trigger_above is True
                assert created_order.symbol == symbol
                assert created_order.origin_price == hedging_limit_price
                assert created_order.origin_quantity == locally_filled_amount
                assert isinstance(created_order.order_group, oco_group.OneCancelsTheOtherOrderGroup)
                group_orders = created_order.order_group.get_group_open_orders()
                assert len(group_orders) == 2
                assert created_order in group_orders
                assert isinstance(created_order.order_group.active_order_swap_strategy, octobot_trading.personal_data.TakeProfitFirstActiveOrderSwapStrategy)
                assert created_order.order_group.active_order_swap_strategy.swap_timeout == spot_hedging_engine._active_order_swap_timeout
                assert created_order.order_group.active_order_swap_strategy.trigger_price_configuration == trading_enums.ActiveOrderSwapTriggerPriceConfiguration.FILLING_PRICE.value
                
                # Verify stop order
                stop_order = [
                    order
                    for order in group_orders
                    if order.order_type == trading_enums.TraderOrderType.STOP_LOSS
                ][0]
                assert isinstance(stop_order, octobot_trading.personal_data.StopLossOrder)
                if is_self_managed:
                    assert stop_order.is_active is True
                    assert stop_order.active_trigger is None
                else:
                    assert stop_order.is_active is False
                    assert isinstance(stop_order.active_trigger, octobot_trading.personal_data.PriceTrigger)
                    assert stop_order.active_trigger.trigger_price == stop_price
                    assert stop_order.active_trigger.trigger_above is False
                assert stop_order.side == trading_enums.TradeOrderSide.SELL
                assert stop_order.symbol == symbol
                assert stop_order.origin_price == stop_price
                assert stop_order.origin_quantity == locally_filled_amount
                assert stop_order.order_group is created_order.order_group
