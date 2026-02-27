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
import mock

import pytest
from octobot_commons.tests.test_config import load_test_config

from tests import event_loop
import octobot_trading.personal_data as personal_data
import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.personal_data.orders.order_factory as order_factory_module
import octobot_trading.storage.orders_storage as orders_storage
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors as trading_errors
from octobot_trading.enums import (
    ExchangeConstantsMarketStatusColumns as Ecmsc,
    TradeOrderSide,
    TradeOrderType,
    TraderOrderType,
    StoredOrdersAttr,
)
from octobot_trading.exchanges.exchange_manager import ExchangeManager
from octobot_trading.exchanges.traders.trader_simulator import TraderSimulator
from octobot_trading.api.exchange import cancel_ccxt_throttle_task
from tests.personal_data.orders import created_order

pytestmark = pytest.mark.asyncio


class TestOrderFactory:
    DEFAULT_SYMBOL = "BTC/USDT"
    EXCHANGE_MANAGER_CLASS_STRING = "binanceus"

    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, TestOrderFactory.EXCHANGE_MANAGER_CLASS_STRING)
        await exchange_manager.initialize(exchange_config_by_exchange=None)

        trader = TraderSimulator(config, exchange_manager)
        await trader.initialize()

        return config, exchange_manager, trader

    @staticmethod
    async def stop(exchange_manager):
        cancel_ccxt_throttle_task()
        await exchange_manager.stop()

    async def test_parse_order_type(self):
        _, exchange_manager, trader_inst = await self.init_default()

        order_to_test = personal_data.Order(trader_inst)
        assert order_to_test.simulated is True

        ccxt_order_buy_market = {
            "side": TradeOrderSide.BUY,
            "type": TradeOrderType.MARKET
        }

        order_to_test.update_from_raw(ccxt_order_buy_market)
        assert order_to_test.order_type == TraderOrderType.BUY_MARKET

        ccxt_order_buy_limit = {
            "side": TradeOrderSide.BUY,
            "type": TradeOrderType.LIMIT
        }
        assert personal_data.parse_order_type(ccxt_order_buy_limit) == (TradeOrderSide.BUY, TraderOrderType.BUY_LIMIT)

        ccxt_order_sell_market = {
            "side": TradeOrderSide.SELL,
            "type": TradeOrderType.MARKET
        }
        assert personal_data.parse_order_type(ccxt_order_sell_market) == (TradeOrderSide.SELL, TraderOrderType.SELL_MARKET)

        ccxt_order_sell_limit = {
            "side": TradeOrderSide.SELL,
            "type": TradeOrderType.LIMIT
        }
        assert personal_data.parse_order_type(ccxt_order_sell_limit) == (TradeOrderSide.SELL, TraderOrderType.SELL_LIMIT)

        ccxt_order_stop_loss_sell = {
            "side": TradeOrderSide.SELL,
            "type": TradeOrderType.STOP_LOSS
        }
        assert personal_data.parse_order_type(ccxt_order_stop_loss_sell) == (TradeOrderSide.SELL, TraderOrderType.STOP_LOSS)

        ccxt_order_stop_loss_buy = {
            "side": TradeOrderSide.BUY,
            "type": TradeOrderType.STOP_LOSS
        }
        assert personal_data.parse_order_type(ccxt_order_stop_loss_buy) == (TradeOrderSide.BUY, TraderOrderType.STOP_LOSS)

        unsupported = {
            "side": TradeOrderSide.BUY,
            "type": TradeOrderType.UNSUPPORTED
        }
        assert personal_data.parse_order_type(unsupported) == (TradeOrderSide.BUY, TraderOrderType.UNSUPPORTED)

        await self.stop(exchange_manager)

    async def test_create_order_from_dict(self):
        price = decimal.Decimal("100")
        quantity = decimal.Decimal("2")
        _, exchange_manager, trader_inst = await self.init_default()
        limit_order = personal_data.create_order_instance(
            trader_inst,
            TraderOrderType.SELL_LIMIT,
            self.DEFAULT_SYMBOL,
            price,
            quantity,
            quantity_filled=decimal.Decimal("0.66"),
            price=price,
            order_id="123",
            tag="tag",
            reduce_only=True,
            exchange_creation_params={"plop": 1, "fake_param": True},
            associated_entry_id="1",
        )
        order_dict = limit_order.to_dict()
        created_from_dict = personal_data.create_order_from_dict(trader_inst, order_dict)
        assert created_from_dict.origin_price == limit_order.origin_price == price
        assert created_from_dict.origin_quantity == limit_order.origin_quantity == quantity
        assert created_from_dict.filled_quantity == limit_order.filled_quantity == decimal.Decimal("0.66")
        assert created_from_dict.__class__ is limit_order.__class__ == personal_data.SellLimitOrder
        assert created_from_dict.symbol == limit_order.symbol == self.DEFAULT_SYMBOL
        assert created_from_dict.order_id == limit_order.order_id == "123"
        assert created_from_dict.tag == limit_order.tag == "tag"
        assert created_from_dict.reduce_only is limit_order.reduce_only is True
        # exchange_creation_params are not copied
        assert created_from_dict.exchange_creation_params == {}
        assert limit_order.exchange_creation_params == {"plop": 1, "fake_param": True}
        # associated_entry_ids are not copied
        assert created_from_dict.associated_entry_ids is None
        assert created_from_dict.trigger_above is limit_order.trigger_above is True
        assert created_from_dict.exchange_order_id # ensure exchange_order_id is generated
        assert limit_order.associated_entry_ids == ["1"]
        assert limit_order.cancel_policy is None


        _, exchange_manager, trader_inst = await self.init_default()
        limit_order = personal_data.create_order_instance(
            trader_inst,
            TraderOrderType.SELL_LIMIT,
            self.DEFAULT_SYMBOL,
            price,
            quantity,
            price=price,
            trigger_above=False,
            exchange_order_id="123",
            cancel_policy=personal_data.create_cancel_policy(
                personal_data.ExpirationTimeOrderCancelPolicy.__name__,
                {
                    "expiration_time": 999
                }
            )
        )
        order_dict = limit_order.to_dict()
        created_from_dict = personal_data.create_order_from_dict(trader_inst, order_dict)
        assert created_from_dict.origin_price == limit_order.origin_price == price
        assert created_from_dict.origin_quantity == limit_order.origin_quantity == quantity
        assert created_from_dict.__class__ is limit_order.__class__ == personal_data.SellLimitOrder
        assert created_from_dict.symbol == limit_order.symbol == self.DEFAULT_SYMBOL
        assert created_from_dict.reduce_only is limit_order.reduce_only is False
        # exchange_creation_params are not copied
        assert created_from_dict.exchange_creation_params == {}
        assert limit_order.exchange_creation_params == {}
        # associated_entry_ids are not copied
        assert created_from_dict.associated_entry_ids is None
        assert created_from_dict.trigger_above is limit_order.trigger_above is False
        assert created_from_dict.exchange_order_id == "123"
        assert limit_order.associated_entry_ids is None
        # cancel policy is not copied
        assert limit_order.cancel_policy == personal_data.ExpirationTimeOrderCancelPolicy(
            expiration_time=999
        )
        assert created_from_dict.cancel_policy is None

        await self.stop(exchange_manager)

    async def test_create_order_from_order_storage_details_with_simple_order(self):
        _, exchange_manager, trader_inst = await self.init_default()
        try:
        
            order = personal_data.BuyLimitOrder(trader_inst)
            order.update(order_type=TraderOrderType.BUY_LIMIT,
                         symbol="BTC/USDT",
                         current_price=decimal.Decimal("70"),
                         quantity=decimal.Decimal("10"),
                         price=decimal.Decimal("70"))
            order.trigger_above = True
            assert order.taker_or_maker == "taker"  # instantly filled limit order taker fee is saved
            order_storage_details = orders_storage._format_order(order, exchange_manager)
            order_storage_details[StoredOrdersAttr.ENTRIES.value] = ["11111"]

            pending_groups = {}
            created_order = await personal_data.create_order_from_order_storage_details(
                order_storage_details, exchange_manager, pending_groups
            )
            assert pending_groups == {}

            assert created_order.exchange_manager is exchange_manager
            assert created_order.origin_quantity == order.origin_quantity
            assert created_order.timestamp == order.timestamp
            assert created_order.creation_time == order.creation_time
            assert created_order.origin_price == order.origin_price
            assert created_order.trigger_above is order.trigger_above is True
            assert created_order.taker_or_maker == "taker"  # instantly filled limit order taker fee is saved
            assert created_order.__class__ is order.__class__
            # associated_entry_ids are added from order_storage_details but not in original order
            assert created_order.associated_entry_ids == ["11111"]
            assert created_order.cancel_policy is None
            assert order.associated_entry_ids is None

            # updated creation_time (as with chained orders): creation_time is used to restore order
            assert created_order.creation_time != 123
            order.creation_time = 123
            order.trigger_above = False

            order_storage_details = orders_storage._format_order(order, exchange_manager)
            created_order = await personal_data.create_order_from_order_storage_details(
                order_storage_details, exchange_manager, pending_groups
            )
            assert pending_groups == {}
            assert created_order.exchange_manager is exchange_manager
            assert created_order.origin_quantity == order.origin_quantity
            assert created_order.timestamp == 123   # aligned with creation time
            assert created_order.creation_time == 123   # aligned with creation time
            assert created_order.origin_price == order.origin_price
            assert created_order.trigger_above is order.trigger_above is False
            assert created_order.__class__ is order.__class__
            # associated_entry_ids are added from order_storage_details but not in original order
            assert created_order.associated_entry_ids is None
            assert created_order.cancel_policy is None
            assert order.associated_entry_ids is None

        finally:
            await self.stop(exchange_manager)

    async def test_create_order_from_order_storage_details_with_trailing_profile(self):
        _, exchange_manager, trader_inst = await self.init_default()

        order = personal_data.BuyLimitOrder(trader_inst)
        trailing_profile = personal_data.FilledTakeProfitTrailingProfile([
            personal_data.TrailingPriceStep(price, price, True)
            for price in (10000, 12000, 13000)
        ])
        order.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal("70"),
                     quantity=decimal.Decimal("10"),
                     price=decimal.Decimal("70"),
                     trailing_profile=trailing_profile)
        order_storage_details = orders_storage._format_order(order, exchange_manager)

        pending_groups = {}
        created_order = await personal_data.create_order_from_order_storage_details(
            order_storage_details, exchange_manager, pending_groups
        )
        assert created_order.trailing_profile == trailing_profile
        await self.stop(exchange_manager)

    async def test_create_order_from_order_storage_details_with_cancel_policy(self):
        _, exchange_manager, trader_inst = await self.init_default()

        order = personal_data.BuyLimitOrder(trader_inst)
        cancel_policy = personal_data.create_cancel_policy(
            personal_data.ExpirationTimeOrderCancelPolicy.__name__,
            {
                "expiration_time": 999
            }
        )
        order.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal("70"),
                     quantity=decimal.Decimal("10"),
                     price=decimal.Decimal("70"),
                     cancel_policy=cancel_policy)
        order_storage_details = orders_storage._format_order(order, exchange_manager)

        pending_groups = {}
        created_order = await personal_data.create_order_from_order_storage_details(
            order_storage_details, exchange_manager, pending_groups
        )
        assert created_order.cancel_policy == cancel_policy
        await self.stop(exchange_manager)
    
    async def test_create_order_from_order_storage_details_with_groups(self):
        _, exchange_manager, trader_inst = await self.init_default()  
        
        order = personal_data.BuyLimitOrder(trader_inst)
        group = exchange_manager.exchange_personal_data.orders_manager.create_group(
            personal_data.OneCancelsTheOtherOrderGroup, group_name="plop",
            active_order_swap_strategy=personal_data.StopFirstActiveOrderSwapStrategy(123)
        )
        order.update(order_type=TraderOrderType.BUY_LIMIT,
                     symbol="BTC/USDT",
                     current_price=decimal.Decimal("70"),
                     quantity=decimal.Decimal("10"),
                     price=decimal.Decimal("70"),
                     group=group)
        order_storage_details = orders_storage._format_order(order, exchange_manager)
        order_storage_details[enums.StoredOrdersAttr.GROUP.value][enums.StoredOrdersAttr.GROUP_ID.value] = "plop2"
    
        pending_groups = {}
        created_order = await personal_data.create_order_from_order_storage_details(
            order_storage_details, exchange_manager, pending_groups
        )
        assert created_order.order_group == personal_data.OneCancelsTheOtherOrderGroup(
            "plop2", exchange_manager.exchange_personal_data.orders_manager,
            active_order_swap_strategy=personal_data.StopFirstActiveOrderSwapStrategy(123)
        )
        assert len(pending_groups) == 1
        assert pending_groups["plop2"].name == "plop2"
        assert pending_groups["plop2"].orders_manager is exchange_manager.exchange_personal_data.orders_manager
        assert pending_groups["plop2"].active_order_swap_strategy == personal_data.StopFirstActiveOrderSwapStrategy(123)
        await self.stop(exchange_manager)

    async def test_create_order_from_order_storage_details_with_chained_orders_with_group_and_trailing_profile_and_cancel_policy(self):
        _, exchange_manager, trader_inst = await self.init_default()
    
        order = personal_data.BuyLimitOrder(trader_inst)
        group_1 = exchange_manager.exchange_personal_data.orders_manager.create_group(
            personal_data.OneCancelsTheOtherOrderGroup,
            active_order_swap_strategy=personal_data.StopFirstActiveOrderSwapStrategy(123)
        )
        group_2 = exchange_manager.exchange_personal_data.orders_manager.create_group(
            personal_data.OneCancelsTheOtherOrderGroup
        )
        chained_order_1 = personal_data.BuyLimitOrder(trader_inst)
        chained_order_2 = personal_data.SellLimitOrder(trader_inst)
        chained_order_3 = personal_data.SellLimitOrder(trader_inst)
        trailing_profile_1 = personal_data.FilledTakeProfitTrailingProfile([
            personal_data.TrailingPriceStep(price, price, True)
            for price in (10000, 12000, 13000)
        ])
        trailing_profile_2 = personal_data.FilledTakeProfitTrailingProfile([
            personal_data.TrailingPriceStep(price, price, False)
            for price in (2222, 13000)
        ])
        cancel_policy = personal_data.create_cancel_policy(
            personal_data.ChainedOrderFillingPriceOrderCancelPolicy.__name__,
        )
        for to_update_order, trailing_profile in zip(
            (order, chained_order_1, chained_order_2, chained_order_3),
            (None, trailing_profile_1, trailing_profile_2, None),
        ):
            to_update_order.update(
                order_type=TraderOrderType.BUY_LIMIT,
                symbol="BTC/USDT",
                current_price=decimal.Decimal("70"),
                quantity=decimal.Decimal("10"),
                price=decimal.Decimal("70"),
                trailing_profile=trailing_profile,
            )
        order.update(cancel_policy=cancel_policy)
        chained_order_1.add_to_order_group(group_1)
        assert chained_order_1.trailing_profile is trailing_profile_1
        chained_order_2.add_to_order_group(group_1)
        assert chained_order_2.trailing_profile is trailing_profile_2
        chained_order_3.add_to_order_group(group_2)
        await chained_order_1.set_as_chained_order(order, False, {}, False)
        await chained_order_2.set_as_chained_order(order, True, {"plop_1": True, "plop_2": {"hi": 1}}, False)
        order.add_chained_order(chained_order_1)
        order.add_chained_order(chained_order_2)
        await chained_order_3.set_as_chained_order(chained_order_1, False, {}, False)
        chained_order_1.add_chained_order(chained_order_3)
        order_storage_details = orders_storage._format_order(order, exchange_manager)
    
        pending_groups = {}
        created_order = await personal_data.create_order_from_order_storage_details(
            order_storage_details, exchange_manager, pending_groups
        )
        assert pending_groups == {
            group_1.name: group_1,
            group_2.name: group_2,
        }
        assert group_1.active_order_swap_strategy.swap_timeout == 123
        assert created_order.trailing_profile is None
        assert created_order.cancel_policy == cancel_policy
        chained_orders = created_order.chained_orders
        assert len(chained_orders) == 2
        for chained_order in chained_orders:
            assert chained_order.order_group is group_1
    
        assert chained_orders[0].triggered_by is created_order
        assert chained_orders[0].has_been_bundled is False
        assert chained_orders[0].exchange_creation_params == {}
        assert chained_orders[0].trailing_profile == trailing_profile_1
        assert chained_orders[1].triggered_by is created_order
        assert chained_orders[1].has_been_bundled is True
        assert chained_orders[1].exchange_creation_params == {"plop_1": True, "plop_2": {"hi": 1}}
        assert chained_orders[1].chained_orders == []
        assert chained_orders[1].trailing_profile == trailing_profile_2
        assert chained_orders[1].cancel_policy is None
        second_level_chained_orders = chained_orders[0].chained_orders
        assert len(second_level_chained_orders) == 1
        assert second_level_chained_orders[0].order_group is group_2
        assert second_level_chained_orders[0].chained_orders == []
        assert second_level_chained_orders[0].triggered_by is chained_orders[0]
        assert second_level_chained_orders[0].has_been_bundled is False
        assert second_level_chained_orders[0].exchange_creation_params == {}
        assert second_level_chained_orders[0].trailing_profile is None  
        assert second_level_chained_orders[0].cancel_policy is None
        await self.stop(exchange_manager)


def _symbol_market():
    return {
        Ecmsc.LIMITS.value: {
            Ecmsc.LIMITS_AMOUNT.value: {
                Ecmsc.LIMITS_AMOUNT_MIN.value: 0.5,
                Ecmsc.LIMITS_AMOUNT_MAX.value: 1000,
            },
            Ecmsc.LIMITS_COST.value: {
                Ecmsc.LIMITS_COST_MIN.value: 1,
                Ecmsc.LIMITS_COST_MAX.value: 2000000000,
            },
            Ecmsc.LIMITS_PRICE.value: {
                Ecmsc.LIMITS_PRICE_MIN.value: 0.5,
                Ecmsc.LIMITS_PRICE_MAX.value: 5000000,
            },
        },
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_PRICE.value: 8,
            Ecmsc.PRECISION_AMOUNT.value: 8,
        },
    }


class TestOrderFactoryClass:
    DEFAULT_SYMBOL = "BTC/USDT"
    EXCHANGE_MANAGER_CLASS_STRING = "binanceus"

    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, TestOrderFactoryClass.EXCHANGE_MANAGER_CLASS_STRING)
        await exchange_manager.initialize(exchange_config_by_exchange=None)
        trader = TraderSimulator(config, exchange_manager)
        await trader.initialize()
        return config, exchange_manager, trader

    @staticmethod
    async def stop(exchange_manager):
        cancel_ccxt_throttle_task()
        await exchange_manager.stop()

    def test_order_factory_validate_raises_when_exchange_manager_none(self):
        factory = order_factory_module.OrderFactory(None, None, None, False, False)
        with pytest.raises(ValueError) as exc_info:
            factory.validate()
        assert "exchange_manager is required" in str(exc_info.value)

    def test_order_factory_validate_succeeds_when_exchange_manager_set(self):
        exchange_manager = mock.Mock()
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        factory.validate()

    def test_order_factory_get_validated_amounts_and_prices_returns_adapted(self):
        exchange_manager = mock.Mock(exchange_name="test_exchange")
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        symbol_market = _symbol_market()
        amount = decimal.Decimal("1")
        price = decimal.Decimal("2")
        result = factory._get_validated_amounts_and_prices(
            "BTC/USDT", amount, price, symbol_market
        )
        assert result == [(decimal.Decimal("1"), decimal.Decimal("2"))]

    def test_order_factory_get_validated_amounts_and_prices_raises_min_amount(self):
        exchange_manager = mock.Mock(exchange_name="test_exchange")
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        symbol_market = _symbol_market()
        amount = decimal.Decimal("0.1")
        price = decimal.Decimal("100")
        with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume) as exc_info:
            factory._get_validated_amounts_and_prices(
                "BTC/USDT", amount, price, symbol_market
            )
        assert "too small" in str(exc_info.value)
        assert "amount" in str(exc_info.value).lower()

    def test_order_factory_get_validated_amounts_and_prices_raises_min_cost(self):
        exchange_manager = mock.Mock(exchange_name="test_exchange")
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        symbol_market = _symbol_market()
        amount = decimal.Decimal("0.5")
        price = decimal.Decimal("1")
        with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume) as exc_info:
            factory._get_validated_amounts_and_prices(
                "BTC/USDT", amount, price, symbol_market
            )
        assert "cost" in str(exc_info.value).lower()

    def test_order_factory_ensure_supported_order_type_raises(self):
        exchange = mock.Mock(is_supported_order_type=mock.Mock(return_value=False))
        exchange_manager = mock.Mock(exchange=exchange, exchange_name="test_exchange")
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        with pytest.raises(trading_errors.NotSupportedOrderTypeError) as exc_info:
            factory._ensure_supported_order_type(enums.TraderOrderType.STOP_LOSS)
        assert exc_info.value.order_type == enums.TraderOrderType.STOP_LOSS

    def test_order_factory_ensure_supported_order_type_succeeds(self):
        exchange = mock.Mock(is_supported_order_type=mock.Mock(return_value=True))
        exchange_manager = mock.Mock(exchange=exchange, exchange_name="test_exchange")
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        factory._ensure_supported_order_type(enums.TraderOrderType.STOP_LOSS)

    @pytest.mark.asyncio
    async def test_order_factory_get_computed_price(self):
        exchange_manager = mock.Mock(exchange_name="test_exchange")
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        ctx = mock.Mock()
        order_price = "50000"
        expected_price = decimal.Decimal("50100")
        mock_get_price = mock.AsyncMock(return_value=expected_price)
        with mock.patch.object(script_keywords, "get_price_with_offset", mock_get_price):
            result = await factory._get_computed_price(ctx, order_price)
        assert result == expected_price
        mock_get_price.assert_called_once_with(
            ctx, order_price, use_delta_type_as_flat_value=True
        )

    @pytest.mark.asyncio
    async def test_order_factory_get_computed_quantity_returns_zero_for_empty_input(self):
        exchange_manager = mock.Mock()
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        ctx = mock.Mock()
        for input_amount in ("", "0"):
            result = await factory._get_computed_quantity(
                ctx, input_amount,
                enums.TradeOrderSide.BUY,
                decimal.Decimal("50000"),
                reduce_only=False,
                allow_holdings_adaptation=False,
            )
            assert result == constants.ZERO

    @pytest.mark.asyncio
    async def test_order_factory_get_computed_quantity_delegates_to_get_amount_from_input_amount(self):
        exchange_manager = mock.Mock()
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        ctx = mock.Mock()
        expected_amount = decimal.Decimal("2")
        mock_get_amount = mock.AsyncMock(return_value=expected_amount)
        with mock.patch.object(script_keywords, "get_amount_from_input_amount", mock_get_amount):
            result = await factory._get_computed_quantity(
                ctx, "2", enums.TradeOrderSide.BUY, decimal.Decimal("50000"),
                reduce_only=False, allow_holdings_adaptation=False,
            )
        assert result == expected_amount
        mock_get_amount.assert_called_once_with(
            context=ctx,
            input_amount="2",
            side="buy",
            reduce_only=False,
            is_stop_order=False,
            use_total_holding=False,
            target_price=decimal.Decimal("50000"),
            allow_holdings_adaptation=False,
        )

    @pytest.mark.asyncio
    async def test_order_factory_create_stop_orders_early_return_when_no_stop_loss_price(self):
        exchange_manager = mock.Mock()
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        ctx = mock.Mock()
        base_order = mock.Mock()
        symbol_market = _symbol_market()
        params = {}
        chained_orders = []
        await factory._create_stop_orders(ctx, base_order, symbol_market, params, chained_orders)
        assert chained_orders == []
        assert params == {}

    @pytest.mark.asyncio
    async def test_order_factory_create_stop_orders_creates_chained_order_when_stop_loss_price_set(self):
        _, exchange_manager, trader_inst = await self.init_default()
        try:
            base_order = created_order(
                personal_data.BuyLimitOrder, enums.TraderOrderType.BUY_LIMIT, trader_inst,
            )
            base_order.update(
                order_type=enums.TraderOrderType.BUY_LIMIT,
                symbol=self.DEFAULT_SYMBOL,
                current_price=decimal.Decimal("50000"),
                quantity=decimal.Decimal("1"),
                price=decimal.Decimal("50000"),
            )
            factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
            ctx = script_keywords.get_base_context_from_exchange_manager(exchange_manager, self.DEFAULT_SYMBOL)
            symbol_market = _symbol_market()
            params = {}
            chained_orders = []
            stop_loss_price = decimal.Decimal("45000")
            adapted_price = decimal.Decimal("45000")
            with mock.patch.object(
                exchange_manager.exchange, "is_supported_order_type", mock.Mock(return_value=True)
            ), mock.patch.object(factory, "_get_computed_price", mock.AsyncMock(return_value=adapted_price)):
                await factory._create_stop_orders(
                    ctx, base_order, symbol_market, params, chained_orders,
                    stop_loss_price=stop_loss_price,
                )
            assert len(chained_orders) == 1
            chained_order = chained_orders[0]
            assert chained_order.order_type == enums.TraderOrderType.STOP_LOSS
            assert chained_order.side == enums.TradeOrderSide.SELL
            assert chained_order.origin_quantity == base_order.origin_quantity
            assert chained_order.origin_price == adapted_price
            assert chained_order.symbol == self.DEFAULT_SYMBOL
        finally:
            await self.stop(exchange_manager)

    @pytest.mark.asyncio
    async def test_order_factory_create_take_profit_orders_early_return_when_no_take_profit_prices(self):
        exchange_manager = mock.Mock()
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        ctx = mock.Mock()
        base_order = mock.Mock()
        symbol_market = _symbol_market()
        params = {}
        chained_orders = []
        await factory._create_take_profit_orders(ctx, base_order, symbol_market, params, chained_orders)
        assert chained_orders == []
        assert params == {}

    @pytest.mark.asyncio
    async def test_order_factory_create_take_profit_orders_invalid_volume_percents(self):
        exchange_manager = mock.Mock(exchange_name="test_exchange")
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        ctx = mock.Mock()
        base_order = mock.Mock(side=enums.TradeOrderSide.BUY, origin_quantity=decimal.Decimal("1"), tag="tag")
        symbol_market = _symbol_market()
        params = {}
        chained_orders = []
        take_profit_prices = [decimal.Decimal("1"), decimal.Decimal("2")]
        take_profit_volume_percents = [decimal.Decimal("50")]
        with pytest.raises(trading_errors.InvalidArgumentError) as exc_info:
            await factory._create_take_profit_orders(
                ctx, base_order, symbol_market, params, chained_orders,
                take_profit_prices=take_profit_prices,
                take_profit_volume_percents=take_profit_volume_percents,
            )
        assert "take profit volume percents" in str(exc_info.value)

    def test_order_factory_create_active_order_swap_strategy(self):
        exchange_manager = mock.Mock()
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        strategy_type = "StopFirstActiveOrderSwapStrategy"
        strategy_params = {"swap_timeout": 123}
        result_strategy = mock.Mock()
        with mock.patch.object(
            personal_data, "create_active_order_swap_strategy",
            return_value=result_strategy,
        ) as create_mock:
            result = factory._create_active_order_swap_strategy(strategy_type, strategy_params)
        assert result is result_strategy
        create_mock.assert_called_once_with(strategy_type, **strategy_params)

    def test_order_factory_create_active_order_swap_strategy_with_none_params(self):
        exchange_manager = mock.Mock()
        factory = order_factory_module.OrderFactory(exchange_manager, None, None, False, False)
        result_strategy = mock.Mock()
        with mock.patch.object(
            personal_data, "create_active_order_swap_strategy",
            return_value=result_strategy,
        ) as create_mock:
            result = factory._create_active_order_swap_strategy("SomeStrategy", None)
        assert result is result_strategy
        create_mock.assert_called_once_with("SomeStrategy", **{})

    @pytest.mark.asyncio
    async def test_order_factory_create_order_on_exchange_with_trading_mode(self):
        order = mock.Mock()
        created_order = mock.Mock()
        trading_mode = mock.Mock()
        trading_mode.create_order = mock.AsyncMock(return_value=created_order)
        exchange_manager = mock.Mock()
        dependencies = mock.Mock()
        factory = order_factory_module.OrderFactory(
            exchange_manager, trading_mode, dependencies, wait_for_creation=True, try_to_handle_unconfigured_symbol=False
        )
        result = await factory.create_order_on_exchange(order)
        assert result is created_order
        trading_mode.create_order.assert_called_once_with(
            order, dependencies=dependencies, wait_for_creation=True
        )

    @pytest.mark.asyncio
    async def test_order_factory_create_order_on_exchange_without_trading_mode(self):
        order = mock.Mock()
        created_order = mock.Mock()
        trader = mock.Mock()
        trader.create_order = mock.AsyncMock(return_value=created_order)
        exchange_manager = mock.Mock(trader=trader)
        factory = order_factory_module.OrderFactory(
            exchange_manager, None, None, wait_for_creation=False, try_to_handle_unconfigured_symbol=False
        )
        result = await factory.create_order_on_exchange(order)
        assert result is created_order
        trader.create_order.assert_called_once_with(order, wait_for_creation=False)

    @pytest.mark.asyncio
    async def test_order_factory_create_base_orders_unsupported_symbol(self):
        _, exchange_manager, _ = await self.init_default()
        try:
            factory = order_factory_module.OrderFactory(
                exchange_manager, None, None, False, try_to_handle_unconfigured_symbol=False
            )
            with pytest.raises(trading_errors.UnSupportedSymbolError) as exc_info:
                await factory.create_base_orders_and_associated_elements(
                    enums.TraderOrderType.BUY_MARKET,
                    "INVALID/XYZ",
                    enums.TradeOrderSide.BUY,
                    "1",
                )
            assert "INVALID/XYZ" in str(exc_info.value) or "not found" in str(exc_info.value).lower()
        finally:
            await self.stop(exchange_manager)

    @pytest.mark.asyncio
    async def test_order_factory_create_base_orders_try_to_handle_unconfigured_symbol(self):
        _, exchange_manager, _ = await self.init_default()
        try:
            factory = order_factory_module.OrderFactory(
                exchange_manager, None, None, False, try_to_handle_unconfigured_symbol=True
            )
            with pytest.raises(NotImplementedError) as exc_info:
                await factory.create_base_orders_and_associated_elements(
                    enums.TraderOrderType.BUY_MARKET,
                    "INVALID/XYZ",
                    enums.TradeOrderSide.BUY,
                    "1",
                )
            assert "try_to_handle_unconfigured_symbol" in str(exc_info.value)
        finally:
            await self.stop(exchange_manager)

    @pytest.mark.asyncio
    async def test_order_factory_create_base_orders_and_associated_elements_success(self):
        _, real_exchange_manager, _ = await self.init_default()
        try:
            symbol = "BTC/USDT"
            symbol_market = _symbol_market()
            current_price = decimal.Decimal("50000")
            portfolio_manager = real_exchange_manager.exchange_personal_data.portfolio_manager
            portfolio_manager.portfolio.portfolio["USDT"] = personal_data.SpotAsset(
                name="USDT",
                available=decimal.Decimal("100000"),
                total=decimal.Decimal("100000"),
            )
            symbol_data = mock.Mock()
            symbol_data.prices_manager.get_mark_price = mock.AsyncMock(return_value=float(current_price))
            exchange_symbols_data = mock.Mock(
                exchange_symbol_data={symbol: symbol_data},
                get_exchange_symbol_data=mock.Mock(return_value=symbol_data),
            )
            exchange = mock.Mock(
                get_market_status=mock.Mock(return_value=symbol_market),
                get_exchange_current_time=mock.Mock(return_value=1234567890),
            )
            exchange_manager = mock.Mock(
                bot_id=None,
                is_margin=False,
                exchange=exchange,
                exchange_symbols_data=exchange_symbols_data,
                trader=real_exchange_manager.trader,
                exchange_name=real_exchange_manager.exchange_name,
                is_future=real_exchange_manager.is_future,
                logger=real_exchange_manager.logger,
                exchange_personal_data=real_exchange_manager.exchange_personal_data,
                exchange_config=real_exchange_manager.exchange_config,
            )
            factory = order_factory_module.OrderFactory(
                exchange_manager, None, None, False, try_to_handle_unconfigured_symbol=False
            )
            result = await factory.create_base_orders_and_associated_elements(
                enums.TraderOrderType.BUY_MARKET,
                symbol,
                enums.TradeOrderSide.BUY,
                "1",
            )
            assert len(result) == 1
            base_order = result[0]
            assert base_order.order_type == enums.TraderOrderType.BUY_MARKET
            assert base_order.symbol == symbol
            assert base_order.origin_quantity == decimal.Decimal("1")
            assert base_order.origin_price == decimal.Decimal("50000")
            assert base_order.side == enums.TradeOrderSide.BUY
        finally:
            await self.stop(real_exchange_manager)
