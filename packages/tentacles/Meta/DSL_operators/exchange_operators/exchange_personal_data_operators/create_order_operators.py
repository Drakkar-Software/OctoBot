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
import typing
import asyncio
import json

import octobot_commons.constants
import octobot_commons.errors
import octobot_commons.signals as commons_signals
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.tentacles_management as tentacles_management

import octobot_trading.personal_data
import octobot_trading.exchanges
import octobot_trading.enums
import octobot_trading.modes
import octobot_trading.errors
import octobot_trading.dsl

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


CREATED_ORDERS_KEY = "created_orders"


_CANCEL_POLICIES_CACHE = {}
def _parse_cancel_policy(kwargs: dict) -> typing.Optional[octobot_trading.personal_data.OrderCancelPolicy]:
    if policy := kwargs.get("cancel_policy"):
        lowercase_policy = policy.casefold()
        if not _CANCEL_POLICIES_CACHE:
            _CANCEL_POLICIES_CACHE.update({
                policy.__name__.casefold(): policy
                for policy in tentacles_management.get_all_classes_from_parent(octobot_trading.personal_data.OrderCancelPolicy)
            })
        try:
            policy_class = _CANCEL_POLICIES_CACHE[lowercase_policy]
            policy_params = kwargs.get("cancel_policy_params")
            parsed_policy_params = json.loads(policy_params.replace("'", '"')) if isinstance(policy_params, str) else policy_params
            return policy_class(**(parsed_policy_params or {})) # type: ignore
        except KeyError:
            raise octobot_commons.errors.InvalidParametersError(
                f"Unknown cancel policy: {policy}. Available policies: {', '.join(_CANCEL_POLICIES_CACHE.keys())}"
            )
    return None


class CreateOrderOperator(exchange_operator.ExchangeOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.param_by_name: dict[str, dsl_interpreter.ComputedOperatorParameterType] = dsl_interpreter.UNINITIALIZED_VALUE # type: ignore

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
            dsl_interpreter.OperatorParameter(name="take_profit_prices", description="the price or price offset of the take profit order(s)", required=False, type=list[str]),
            dsl_interpreter.OperatorParameter(name="take_profit_volume_percents", description="% volume of the entry for each take profit", required=False, type=list[float]),
            dsl_interpreter.OperatorParameter(name="stop_loss_price", description="the stop loss price or price offset of the order", required=False, type=str),
            dsl_interpreter.OperatorParameter(name="trailing_profile", description="the trailing profile of the order", required=False, type=dict),
            dsl_interpreter.OperatorParameter(name="cancel_policy", description="the cancel policy of the order", required=False, type=str),
            dsl_interpreter.OperatorParameter(name="cancel_policy_params", description="the cancel policy params of the order", required=False, type=dict),
            dsl_interpreter.OperatorParameter(name="active_order_swap_strategy", description="the type of the active order swap strategy", required=False, type=str),
            dsl_interpreter.OperatorParameter(name="active_order_swap_strategy_params", description="the params of the active order swap strategy", required=False, type=dict),
            dsl_interpreter.OperatorParameter(name="params", description="additional  params for the order", required=False, type=dict),
            dsl_interpreter.OperatorParameter(name="allow_holdings_adaptation", description="allow reducing the order amount to account for available holdings", required=False, type=bool),
        ]

    def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
        local_dependencies = []
        if symbol := self.get_input_value_by_parameter().get("symbol"):
            local_dependencies.append(octobot_trading.dsl.SymbolDependency(symbol=symbol))
        return super().get_dependencies() + local_dependencies

    async def create_base_orders_and_associated_elements(self) -> list[octobot_trading.personal_data.Order]:
        order_factory = self.get_order_factory()
        maybe_cancel_policy = _parse_cancel_policy(self.param_by_name)
        try:
            amount = self.param_by_name["amount"]
            if not amount:
                raise octobot_commons.errors.InvalidParameterFormatError("amount is missing")
            orders = await order_factory.create_base_orders_and_associated_elements(
                order_type=self.param_by_name["order_type"],
                symbol=self.param_by_name["symbol"],
                side=octobot_trading.enums.TradeOrderSide(self.param_by_name["side"]),
                amount=amount,
                price=self.param_by_name.get("price", None),
                reduce_only=self.param_by_name.get("reduce_only", False),
                allow_holdings_adaptation=self.param_by_name.get("allow_holdings_adaptation", False),
                tag=self.param_by_name.get("tag", None),
                exchange_creation_params=self.param_by_name.get("params", None),
                cancel_policy=maybe_cancel_policy,
                stop_loss_price=self.param_by_name.get("stop_loss_price", None),
                take_profit_prices=self.param_by_name.get("take_profit_prices", None),
                take_profit_volume_percents=self.param_by_name.get("take_profit_volume_percents", None),
                trailing_profile_type=self.param_by_name.get("trailing_profile", None),
                active_order_swap_strategy_type=self.param_by_name.get(
                    "active_order_swap_strategy", octobot_trading.personal_data.StopFirstActiveOrderSwapStrategy.__name__
                ),
                active_order_swap_strategy_params=self.param_by_name.get("active_order_swap_strategy_params", {}),
            )
        except octobot_trading.errors.UnSupportedSymbolError as e:
            raise octobot_commons.errors.InvalidParametersError(
                f"Invalid parameters: {e}"
            ) from e
        except octobot_trading.errors.InvalidArgumentError as e:
            raise octobot_commons.errors.InvalidParameterFormatError(e) from e
        except asyncio.TimeoutError as e:
            raise octobot_commons.errors.DSLInterpreterError(
                f"Impossible to create order for {self.param_by_name["symbol"]} on {order_factory.exchange_manager.exchange_name}: {e} and is necessary to compute the order details."
            )
        return orders

    async def pre_compute(self) -> None:
        await super().pre_compute()
        self.param_by_name = self.get_computed_value_by_parameter()
        self.param_by_name["order_type"] = self.get_order_type()
        order_factory = self.get_order_factory()
        orders = await self.create_base_orders_and_associated_elements()
        created_orders = []
        for order in orders:
            created_order = await order_factory.create_order_on_exchange(order)
            if created_order is None:
                raise octobot_commons.errors.DSLInterpreterError(
                    f"Failed to create {order.symbol} {order.order_type.name} order on {order.exchange_manager.exchange_name}"
                )
            else:
                created_orders.append(created_order)
        self.value = {CREATED_ORDERS_KEY: [order.to_dict() for order in created_orders]}

    def get_order_type(self) -> octobot_trading.enums.TraderOrderType:
        raise NotImplementedError("get_order_type must be implemented")

    def get_order_factory(self) -> octobot_trading.personal_data.OrderFactory:
        raise NotImplementedError("get_order_factory must be implemented")

def create_create_order_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
    trading_mode: typing.Optional[octobot_trading.modes.AbstractTradingMode] = None,
    dependencies: typing.Optional[commons_signals.SignalDependencies] = None,
    wait_for_creation: bool = True,
    try_to_handle_unconfigured_symbol: bool = False,
) -> list[type[CreateOrderOperator]]:
    _order_factory = octobot_trading.personal_data.OrderFactory(
        exchange_manager, trading_mode, dependencies, wait_for_creation, try_to_handle_unconfigured_symbol
    )

    class _FactoryMixin:
        def get_order_factory(self) -> octobot_trading.personal_data.OrderFactory:
            try:
                _order_factory.validate()
            except ValueError as e:
                raise octobot_commons.errors.DSLInterpreterError(e) from e
            return _order_factory
    
    class _MarketOrderOperator(_FactoryMixin, CreateOrderOperator):
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
    
    class _LimitOrderOperator(_FactoryMixin, CreateOrderOperator):
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
    
    class _StopLossOrderOperator(_FactoryMixin, CreateOrderOperator):
        DESCRIPTION = "Creates a stop market order"
        EXAMPLE = "stop_loss('buy', 'BTC/USDT', 0.01, price='-1%')"

        @staticmethod
        def get_name() -> str:
            return "stop_loss"


        async def pre_compute(self) -> None:
            self.get_order_factory()._ensure_supported_order_type(
                octobot_trading.enums.TraderOrderType.STOP_LOSS
            )
            return await super().pre_compute()

        @classmethod
        def get_second_required_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(name="price", description="the trigger price of the order: a flat or offset price", required=True, type=str),
            ]

        def get_order_type(self) -> octobot_trading.enums.TraderOrderType:
            return octobot_trading.enums.TraderOrderType.STOP_LOSS

    return [
        _MarketOrderOperator,
        _LimitOrderOperator,
        _StopLossOrderOperator,
    ]