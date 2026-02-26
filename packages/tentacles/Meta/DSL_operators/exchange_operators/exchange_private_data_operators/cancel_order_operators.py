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
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.exchanges
import octobot_trading.enums

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


def create_cancel_order_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
    wait_for_cancelling: bool = True,
) -> list:

    class _CancelOrderOperator(exchange_operator.ExchangeOperator):
        DESCRIPTION = "Cancels one or many orders"
        EXAMPLE = "cancel_order('1234567890')"

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

        async def pre_compute(self) -> None:
            await super().pre_compute()
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
                if await exchange_manager.trader.cancel_order(
                    order, wait_for_cancelling=wait_for_cancelling
                ):
                    cancelled_order_ids.append(order.exchange_order_id)
            self.value = cancelled_order_ids


    return [
        _CancelOrderOperator,
    ]
