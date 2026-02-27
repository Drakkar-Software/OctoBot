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

import octobot_commons.constants
import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.signals
import octobot_trading.exchanges
import octobot_trading.enums
import octobot_trading.errors
import octobot_trading.modes.abstract_trading_mode
import octobot_trading.dsl

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


CANCELLED_ORDERS_KEY = "cancelled_orders"


def create_cancel_order_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
    trading_mode: typing.Optional[octobot_trading.modes.abstract_trading_mode.AbstractTradingMode] = None,
    dependencies: typing.Optional[octobot_commons.signals.SignalDependencies] = None,
    wait_for_cancelling: bool = True,
) -> list:

    class _CancelOrderOperator(exchange_operator.ExchangeOperator):
        DESCRIPTION = "Cancels one or many orders"
        EXAMPLE = "cancel_order('BTC/USDT', side='buy')"

        @staticmethod
        def get_name() -> str:
            return "cancel_order"

        @staticmethod
        def get_library() -> str:
            # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
            return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(name="symbol", description="the symbol of the orders to cancel", required=True, type=str, default=None),
                dsl_interpreter.OperatorParameter(name="side", description="the side of the orders to cancel", required=False, type=str, default=None),
                dsl_interpreter.OperatorParameter(name="tag", description="the tag of the orders to cancel", required=False, type=str, default=None),
                dsl_interpreter.OperatorParameter(name="exchange_order_ids", description="the exchange id of the orders to cancel", required=False, type=list[str], default=None),
            ]

        def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
            local_dependencies = []
            if symbol := self.get_input_value_by_parameter().get("symbol"):
                local_dependencies.append(octobot_trading.dsl.SymbolDependency(symbol=symbol))
            return super().get_dependencies() + local_dependencies

        async def pre_compute(self) -> None:
            await super().pre_compute()
            if exchange_manager is None:
                raise octobot_commons.errors.DSLInterpreterError(
                    "exchange_manager is required for cancel_order operator"
                )
            cancelled_order_ids = []
            param_by_name = self.get_computed_value_by_parameter()
            if side := param_by_name.get("side"):
                side = octobot_trading.enums.TradeOrderSide(side)
            exchange_order_ids = param_by_name.get("exchange_order_ids")
            to_cancel = [
                order
                for order in exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
                    symbol=param_by_name.get("symbol"), tag=param_by_name.get("tag"), active=None
                )
                if (
                    not (order.is_cancelled() or order.is_closed())
                    and (side is None or (side is order.side))
                    and (exchange_order_ids is None or (order.exchange_order_id in exchange_order_ids)) # type: ignore
                )
            ]
            for order in to_cancel:
                if trading_mode:
                    cancelled, _ = await trading_mode.cancel_order(
                        order, wait_for_cancelling=wait_for_cancelling, dependencies=dependencies
                    )
                else:
                    cancelled = await exchange_manager.trader.cancel_order(
                        order, wait_for_cancelling=wait_for_cancelling
                    )
                if cancelled:
                    cancelled_order_ids.append(order.exchange_order_id)
            if not cancelled_order_ids:
                description = {k: v for k, v in param_by_name.items() if v}
                raise octobot_trading.errors.OrderDescriptionNotFoundError(
                    f"No [{exchange_manager.exchange_name}] order found matching {description}"
                )
            self.value = {CANCELLED_ORDERS_KEY: cancelled_order_ids}


    return [
        _CancelOrderOperator,
    ]
