#  Drakkar-Software OctoBot-Commons
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
import dataclasses
import typing
import decimal
import asyncio
import json

import octobot_commons.constants
import octobot_commons.errors
import octobot_commons.logging
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.tentacles_management as tentacles_management
import octobot_trading.personal_data
import octobot_trading.exchanges
import octobot_trading.api
import octobot_trading.enums
import octobot_trading.constants
import octobot_trading.modes.script_keywords as script_keywords

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


_CANCEL_POLICIES_CACHE = {}


@dataclasses.dataclass
class _OrderDetails:
    input_price: decimal.Decimal
    input_quantity_ratio: decimal.Decimal


class _OrderFactory:
    def __init__(
        self,
        exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
        wait_for_creation: bool = True,
    ):
        self.exchange_manager = exchange_manager
        self.wait_for_creation = wait_for_creation

    def create_order_instance(self, **kwargs: typing.Any) -> octobot_trading.personal_data.Order:
            # todo
            current_price = 1 #todo
            computed_price = decimal.Decimal(str(kwargs["price"])) if kwargs["price"] is not None else None
            computed_stop_price = decimal.Decimal(str(kwargs["stop_price"])) if kwargs["stop_price"] is not None else None
            group = None #todo
            exchange_creation_params = None #todo
            trailing_profile = None #todo
            cancel_policy = None #todo
            # todo handle chained TP & SL orders
            return octobot_trading.personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=kwargs["order_type"],
                symbol=kwargs["symbol"],
                current_price=current_price,
                quantity=decimal.Decimal(str(kwargs["quantity"])),
                price=computed_price,
                stop_price=computed_stop_price,
                side=kwargs["side"],
                group=group,
                tag=kwargs.get("tag", None),
                reduce_only=kwargs.get("reduce_only", None),
                exchange_creation_params=exchange_creation_params,
                trailing_profile=trailing_profile,
                cancel_policy=cancel_policy,
            )

    def _get_validated_price_and_amount(
        self, symbol: str, price: decimal.Decimal, amount: decimal.Decimal, symbol_market
    ) -> tuple[decimal.Decimal, decimal.Decimal]:
        quantities_and_prices = octobot_trading.personal_data.decimal_check_and_adapt_order_details_if_necessary(
            amount, price, symbol_market
        )
        if len(quantities_and_prices) == 0:
            min_amount = octobot_trading.personal_data.get_minimal_order_amount(symbol_market)
            if amount < min_amount:
                raise octobot_commons.errors.InvalidParametersError(
                    f"An order amount of {amount} is too small to trade {symbol} on {self.exchange_manager.exchange_name}. Minimum amount is {min_amount}."
                )
            cost = price * amount
            min_cost = octobot_trading.personal_data.get_minimal_order_cost(symbol_market)
            if cost < min_cost:
                raise octobot_commons.errors.InvalidParametersError(
                    f"An order cost of {cost} is too small to trade {symbol} on {self.exchange_manager.exchange_name}. Minimum cost is {min_cost}."
                )
        if len(quantities_and_prices) > 1:
            raise octobot_commons.errors.InvalidParametersError(
                f"An order cost of {price * amount} is too large to trade {symbol} on {self.exchange_manager.exchange_name}"
            )
        return quantities_and_prices[0]

    def _parse_cancel_policy(self, kwargs: dict) -> typing.Optional[octobot_trading.personal_data.OrderCancelPolicy]:
        if policy := kwargs.get("cancel_policy"):
            lowercase_policy = policy.casefold()
            if not _CANCEL_POLICIES_CACHE:
                _CANCEL_POLICIES_CACHE.update({
                    policy.__name__.casefold(): policy.__name__
                    for policy in tentacles_management.get_all_classes_from_parent(octobot_trading.personal_data.OrderCancelPolicy)
                })
            try:
                policy_class = _CANCEL_POLICIES_CACHE[lowercase_policy]
                policy_params = kwargs.get("cancel_policy_params")
                parsed_policy_params = json.loads(policy_params.replace("'", '"')) if isinstance(policy_params, str) else policy_params
                return policy_class(**parsed_policy_params) # type: ignore
            except KeyError:
                raise octobot_commons.errors.InvalidParametersError(
                    f"Unknown cancel policy: {policy}. Available policies: {', '.join(_CANCEL_POLICIES_CACHE.keys())}"
                )
        return None

    async def _get_computed_price(self, ctx: script_keywords.Context, order_price: str) -> decimal.Decimal:
        return await script_keywords.get_price_with_offset(ctx, order_price, use_delta_type_as_flat_value=True)

    async def _get_computed_quantity(
        self, ctx: script_keywords.Context, input_amount: str, 
        side: octobot_trading.enums.TradeOrderSide, target_price: decimal.Decimal, reduce_only: bool
    ):
        if input_amount == "0":
            return octobot_trading.constants.ZERO
        return await script_keywords.get_amount_from_input_amount(
            context=ctx,
            input_amount=input_amount,
            side=side.value,
            reduce_only=reduce_only,
            is_stop_order=False,
            use_total_holding=False,
            target_price=target_price,
            # raise when not enough funds to create an order according to user input
            allow_holdings_adaptation=False,
        )

    async def register_chained_order(
        self, main_order, price, order_type, side, quantity=None, allow_bundling=True, tag=None, reduce_only=False,
        update_with_triggering_order_fees=None
    ) -> tuple:
        chained_order = octobot_trading.personal_data.create_order_instance(
            trader=self.exchange_manager.trader,
            order_type=order_type,
            symbol=main_order.symbol,
            current_price=price,
            quantity=quantity or main_order.origin_quantity,
            price=price,
            side=side,
            associated_entry_id=main_order.order_id,
            reduce_only=reduce_only,
            tag=tag,
        )
        params = {}
        # do not reduce chained order amounts to account for fees when trading futures
        if update_with_triggering_order_fees is None:
            update_with_triggering_order_fees = not self.exchange_manager.is_future
        if allow_bundling:
            params = await self.exchange_manager.trader.bundle_chained_order_with_uncreated_order(
                main_order, chained_order, update_with_triggering_order_fees
            )
        else:
            await self.exchange_manager.trader.chain_order(
                main_order, chained_order, update_with_triggering_order_fees, False
            )
        return params, chained_order

    async def _create_stop_orders(
        self, base_order: octobot_trading.personal_data.Order, symbol_market: dict,
        params: dict, chained_orders: list[octobot_trading.personal_data.Order], kwargs: dict
    ):
        stop_loss_price = kwargs.get("stop_loss_price")
        if not stop_loss_price:
            return
        stop_price = octobot_trading.personal_data.decimal_adapt_price(
            symbol_market,
            stop_loss_price
        )
        exit_side = (
            octobot_trading.enums.TradeOrderSide.SELL 
            if base_order.side == octobot_trading.enums.TradeOrderSide.BUY else octobot_trading.enums.TradeOrderSide.BUY
        )
        param_update, chained_order = await octobot_trading.personal_data.create_and_register_chained_order_on_base_order(
            base_order, stop_price, octobot_trading.enums.TraderOrderType.STOP_LOSS, exit_side,
            quantity=base_order.origin_quantity, tag=base_order.tag,
            reduce_only=self.exchange_manager.is_future,
        )
        params.update(param_update)
        chained_orders.append(chained_order)

    async def _create_take_profit_orders(
        self, ctx: script_keywords.Context, base_order: octobot_trading.personal_data.Order, symbol_market: dict,
        params: dict, chained_orders: list[octobot_trading.personal_data.Order], kwargs: dict
    ):
        take_profit_prices = kwargs.get("take_profit_prices")
        if not take_profit_prices:
            return
        take_profit_volume_percents = kwargs.get("take_profit_volume_percents") or []
        if len(take_profit_volume_percents) not in (0, len(take_profit_prices)):
            raise octobot_commons.errors.InvalidParametersError(
                f"There must be either 0 or as many take profit volume percents as take profit prices"
            )
        exit_side = (
            octobot_trading.enums.TradeOrderSide.SELL 
            if base_order.side == octobot_trading.enums.TradeOrderSide.BUY else octobot_trading.enums.TradeOrderSide.BUY
        )
        take_profit_order_details = [
            _OrderDetails(
                take_profit_price,
                take_profit_volume_percents[i] / octobot_trading.constants.ONE_HUNDRED if take_profit_volume_percents else (
                    octobot_trading.constants.ONE / len(take_profit_prices)
                )
            )
            for i, take_profit_price in enumerate(take_profit_prices)
        ]
        for index, take_profits_detail in enumerate(take_profit_order_details):
            is_last = index == len(take_profit_order_details) - 1
            price = await self._get_computed_price(ctx, take_profits_detail.input_price)
            quantity = octobot_trading.personal_data.decimal_adapt_quantity(
                symbol_market, base_order.origin_quantity * take_profits_detail.input_quantity_ratio
            )
            order_type = self.exchange_manager.trader.get_take_profit_order_type(
                base_order,
                octobot_trading.enums.TraderOrderType.SELL_LIMIT if exit_side is octobot_trading.enums.TradeOrderSide.SELL
                else octobot_trading.enums.TraderOrderType.BUY_LIMIT
            )
            param_update, chained_order = await octobot_trading.personal_data.create_and_register_chained_order_on_base_order(
                base_order, price, order_type, exit_side,
                quantity=quantity, tag=base_order.tag, reduce_only=self.exchange_manager.is_future,
                # only the last order is to take trigger fees into account
                update_with_triggering_order_fees=is_last and not self.exchange_manager.is_future
            )
            params.update(param_update)
            chained_orders.append(chained_order)

    def _create_active_order_swap_strategy(self, kwargs: dict) -> octobot_trading.personal_data.ActiveOrderSwapStrategy:
        strategy_type = kwargs.get("active_order_swap_strategy", octobot_trading.personal_data.StopFirstActiveOrderSwapStrategy.__name__)
        octobot_trading.personal_data.create_active #todo
        return strategy_type(kwargs.get(
            "active_order_swap_timeout", octobot_trading.constants.ACTIVE_ORDER_STRATEGY_SWAP_TIMEOUT
        ))

    async def _create_base_order_associated_elements(
        self, ctx: script_keywords.Context, base_order: octobot_trading.personal_data.Order, symbol_market: dict, kwargs: dict
    ) -> None:
        # create chained orders
        params = {}
        chained_orders = []
        await self._create_stop_orders(base_order, symbol_market, params, chained_orders, kwargs)
        await self._create_take_profit_orders(ctx, base_order, symbol_market, params, chained_orders, kwargs)
        stop_orders = [o for o in chained_orders if octobot_trading.personal_data.is_stop_order(o.order_type)]
        tp_orders = [o for o in chained_orders if not octobot_trading.personal_data.is_stop_order(o.order_type)]
        if stop_orders and tp_orders:

            active_order_swap_strategy = self._create_active_order_swap_strategy(kwargs)
            trailing_profile_type = kwargs.get("trailing_profile")
            if len(stop_orders) == len(tp_orders):
                group_type = octobot_trading.personal_data.OneCancelsTheOtherOrderGroup
            elif trailing_profile_type == octobot_trading.personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT:
                group_type = octobot_trading.personal_data.TrailingOnFilledTPBalancedOrderGroup
                entry_price = base_order.origin_price
                for stop_order in stop_orders:
                    # register trailing profile in stop orders
                    stop_order.trailing_profile = octobot_trading.personal_data.create_filled_take_profit_trailing_profile(
                        entry_price, tp_orders
                    )
            else:
                group_type = octobot_trading.personal_data.BalancedTakeProfitAndStopOrderGroup
            oco_group = self.exchange_manager.exchange_personal_data.orders_manager.create_group(
                group_type, active_order_swap_strategy=active_order_swap_strategy
            )
            for order in chained_orders:
                order.add_to_order_group(oco_group)
            # in futures, inactive orders are not necessary
            if self.exchange_manager.trader.enable_inactive_orders and not self.exchange_manager.is_future:
                await oco_group.active_order_swap_strategy.apply_inactive_orders(chained_orders)


    async def create_base_order_and_associated_elements(self, **kwargs: typing.Any) -> octobot_trading.personal_data.Order:
        symbol = kwargs["symbol"]
        side = octobot_trading.enums.TradeOrderSide(kwargs["side"])
        try:
            current_price = await octobot_trading.personal_data.get_up_to_date_price(
                self.exchange_manager, symbol=symbol, timeout=octobot_trading.constants.ORDER_DATA_FETCHING_TIMEOUT
            )
            symbol_market = self.exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
            order_price = kwargs.get("price", None) # market orders have no price
            ctx = script_keywords.get_base_context_from_exchange_manager(self.exchange_manager, symbol)
            computed_price = current_price if order_price is None else await self._get_computed_price(ctx, order_price)
            reduce_only = kwargs.get("reduce_only", False)
            computed_amount = await self._get_computed_quantity(ctx, kwargs["amount"], side, computed_price, reduce_only)
            valid_price, valid_amount = self._get_validated_price_and_amount(symbol, computed_price, computed_amount, symbol_market)
            maybe_cancel_policy = self._parse_cancel_policy(kwargs)
            base_order = octobot_trading.personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=kwargs["order_type"],
                symbol=symbol,
                current_price=current_price,
                quantity=valid_amount,
                price=valid_price,
                side=side,
                tag=kwargs.get("tag"),
                reduce_only=reduce_only,
                exchange_creation_params=kwargs.get("params"),
                cancel_policy=maybe_cancel_policy,
            )
            await self._create_base_order_associated_elements(base_order, kwargs)
            return base_order
        except asyncio.TimeoutError as e:
            self._logger().error(
                f"Impossible to create order for {symbol} on {self.exchange_manager.exchange_name}: {e} and is necessary to compute the order details."
            )
            raise octobot_commons.errors.DSLInterpreterError(
                f"Failed to create base order and associated elements: {e}"
            )

    async def create_order_on_exchange(
        self, order: octobot_trading.personal_data.Order
    ) -> typing.Optional[octobot_trading.personal_data.Order]:
        if created_order := await self.exchange_manager.trader.create_order(order, wait_for_creation=self.wait_for_creation):
            return created_order
        raise octobot_commons.errors.DSLInterpreterError("Failed to create order on exchange")
    
    def _logger(self) -> octobot_commons.logging.BotLogger:
        return octobot_commons.logging.get_logger(f"{self.__class__.__name__} | {self.exchange_manager.exchange_name}")



class OrderOperator(exchange_operator.ExchangeOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.param_by_name: dict[str, dsl_interpreter.ComputedOperatorParameterType] = exchange_operator.UNINITIALIZED_VALUE # type: ignore
        self.created_order: typing.Optional[octobot_trading.personal_data.Order] = exchange_operator.UNINITIALIZED_VALUE # type: ignore

    @staticmethod
    def get_library() -> str:
        # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
        return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return (
            cls.get_first_required_parameters() +
            cls.get_second_required_parameters() +
            cls.get_last_parameters()
        )

    @classmethod
    def get_first_required_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="side", description="the side of the order", required=True, type=str),
            dsl_interpreter.OperatorParameter(name="symbol", description="the symbol of the order", required=True, type=str),
            dsl_interpreter.OperatorParameter(name="amount", description="the amount of the order", required=True, type=float),
        ]

    @classmethod
    def get_second_required_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return []

    @classmethod
    def get_last_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="reduce_only", description="whether the order is reduce only", required=False, type=bool),
            dsl_interpreter.OperatorParameter(name="tag", description="the tag of the order", required=False, type=str),
            dsl_interpreter.OperatorParameter(name="leverage", description="the leverage of the order", required=False, type=int),
            dsl_interpreter.OperatorParameter(name="take_profit_prices", description="the price or price offset of the take profit order(s)", required=False, type=list[str]),
            dsl_interpreter.OperatorParameter(name="take_profit_volume_percents", description="% volume of the entry for each take profit", required=False, type=list[float]),
            dsl_interpreter.OperatorParameter(name="stop_loss_price", description="the stop loss price or price offset of the order", required=False, type=str),
            dsl_interpreter.OperatorParameter(name="trailing_profile", description="the trailing profile of the order", required=False, type=dict),
            dsl_interpreter.OperatorParameter(name="cancel_policy", description="the cancel policy of the order", required=False, type=str),
            dsl_interpreter.OperatorParameter(name="cancel_policy_params", description="the cancel policy params of the order", required=False, type=dict),
            dsl_interpreter.OperatorParameter(name="active_order_swap_timeout", description="the timeout for the active order swap strategy", required=False, type=int),
            dsl_interpreter.OperatorParameter(name="params", description="additional  params for the order", required=False, type=dict),
        ]

    def get_order_factory(self) -> _OrderFactory:
        raise NotImplementedError("get_order_factory must be implemented")

    async def pre_compute(self) -> None:
        await super().pre_compute()
        param_by_name = self.get_computed_value_by_parameter()
        order = await self.get_order_factory().create_base_order_and_associated_elements(**param_by_name)
        self.created_order = await self.get_order_factory().create_order_on_exchange(order)

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        if self.created_order is exchange_operator.UNINITIALIZED_VALUE:
            raise octobot_commons.errors.DSLInterpreterError("{self.__class__.__name__} has not been pre_computed")
        if self.created_order is None:
            raise octobot_commons.errors.DSLInterpreterError("Created order is None")
        return self.created_order.to_dict()


def create_order_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
    wait_for_creation: bool = True,
) -> list[type[OrderOperator]]:
    _order_factory = _OrderFactory(exchange_manager, wait_for_creation)

    class _FactoryMixin:
        def get_order_factory(self) -> _OrderFactory:
            return _order_factory
    
    class _MarketOrderOperator(OrderOperator, _FactoryMixin):
        DESCRIPTION = "Creates a market order"
        EXAMPLE = "market('buy', 'BTC/USDT', 0.01)"

        @staticmethod
        def get_name() -> str:
            return "market"

        def get_order_type(self) -> octobot_trading.enums.TraderOrderType:
            return (
                octobot_trading.enums.TraderOrderType.BUY_MARKET
                if self.param_by_name["side"] == octobot_trading.enums.TradeOrderSide.BUY.value else octobot_trading.enums.TraderOrderType.SELL_MARKET
            )
    
    class _LimitOrderOperator(OrderOperator, _FactoryMixin):
        DESCRIPTION = "Creates a limit order"
        EXAMPLE = "limit('buy', 'BTC/USDT', 0.01, price='-1%')"

        @staticmethod
        def get_name() -> str:
            return "limit"

        @classmethod
        def get_second_required_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(name="price", description="the limit price of the order: a flat or offset price", required=True, type=str),
            ]

        def get_order_type(self) -> octobot_trading.enums.TraderOrderType:
            return (
                octobot_trading.enums.TraderOrderType.BUY_LIMIT
                if self.param_by_name["side"] == octobot_trading.enums.TradeOrderSide.BUY.value else octobot_trading.enums.TraderOrderType.SELL_LIMIT
            )
    
    class _StopLossOrderOperator(OrderOperator, _FactoryMixin):
        DESCRIPTION = "Creates a stop market order"
        EXAMPLE = "stop_loss('buy', 'BTC/USDT', 0.01, price='-1%')"

        @staticmethod
        def get_name() -> str:
            return "stop_loss"

        @classmethod
        def get_second_required_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(name="price", description="the trigger price of the order: a flat or offset price", required=True, type=str),
            ]

        def get_order_type(self) -> octobot_trading.enums.TraderOrderType:
            return octobot_trading.enums.TraderOrderType.STOP_LOSS

    return [
        _MarketOrderOperator,
    ]