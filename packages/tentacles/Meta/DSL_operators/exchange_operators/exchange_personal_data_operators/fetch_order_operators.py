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
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges
import octobot_trading.personal_data as personal_data
import octobot_trading.dsl

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


def _trade_to_order_dict_for_fetch(order_trade: personal_data.Trade) -> dict:
    order_dict = dict(order_trade.to_dict())
    order_dict[trading_enums.ExchangeConstantsOrderColumns.FILLED.value] = (
        order_trade.executed_quantity if order_trade.has_been_executed() else trading_constants.ZERO
    )
    return order_dict


def _try_simulated_fetch_order_from_trades(
    exchange_manager: octobot_trading.exchanges.ExchangeManager,
    symbol: str,
    exchange_order_id: str,
) -> typing.Optional[dict]:
    matching_trades = [
        trade_item
        for trade_item in exchange_manager.exchange_personal_data.trades_manager.get_trades(
            exchange_order_id=exchange_order_id
        )
        if trade_item.symbol == symbol
    ]
    if not matching_trades:
        return None
    selected_trade = max(matching_trades, key=lambda trade_item: trade_item.get_time())
    return personal_data.create_order_from_dict(
        exchange_manager.trader,
        _trade_to_order_dict_for_fetch(selected_trade),
    ).to_dict()


def _resolve_simulated_fetch_order_dict(
    exchange_manager: octobot_trading.exchanges.ExchangeManager,
    symbol: str,
    exchange_order_id: str,
) -> dict:
    orders_manager = exchange_manager.exchange_personal_data.orders_manager
    try:
        managed_order = orders_manager.get_order(None, exchange_order_id=exchange_order_id)
    except KeyError:
        from_trades = _try_simulated_fetch_order_from_trades(
            exchange_manager, symbol, exchange_order_id
        )
        if from_trades is not None:
            return from_trades
        raise octobot_commons.errors.InvalidParametersError(
            f"No [{exchange_manager.exchange_name}] order found for symbol={symbol!r} "
            f"exchange_order_id={exchange_order_id!r}"
        ) from None
    if managed_order.symbol != symbol:
        raise octobot_commons.errors.InvalidParametersError(
            f"Order exchange_order_id={exchange_order_id!r} is for symbol "
            f"{managed_order.symbol!r}, not {symbol!r}"
        )
    return managed_order.to_dict()


async def _resolve_real_trading_fetch_order_dict(
    exchange_manager: octobot_trading.exchanges.ExchangeManager,
    symbol: str,
    exchange_order_id: str,
) -> dict:
    if raw_order := await exchange_manager.exchange.get_order(exchange_order_id, symbol=symbol):
        return personal_data.create_order_instance_from_raw(
            exchange_manager.trader, raw_order
        ).to_dict()
    raise octobot_commons.errors.InvalidParametersError(
        f"No [{exchange_manager.exchange_name}] order found for symbol={symbol!r} "
        f"exchange_order_id={exchange_order_id!r}"
    )


def create_fetch_order_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager]
) -> list:

    class _FetchOrderOperator(exchange_operator.ExchangeOperator):
        DESCRIPTION = "Fetches one order from the exchange by symbol and exchange order id"
        EXAMPLE = "fetch_order('BTC/USDT', exchange_order_id='12345')"

        @staticmethod
        def get_name() -> str:
            return "fetch_order"

        @staticmethod
        def get_library() -> str:
            return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(
                    name="symbol", description="the symbol of the order", required=True, type=str, default=None
                ),
                dsl_interpreter.OperatorParameter(
                    name="exchange_order_id",
                    description="the exchange id of the order",
                    required=True,
                    type=str,
                    default=None,
                ),
            ]

        def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
            local_dependencies = []
            if symbol := self.get_input_value_by_parameter().get("symbol"):
                local_dependencies.append(octobot_trading.dsl.SymbolDependency(symbol=symbol))
            return super().get_dependencies() + local_dependencies

        async def pre_compute(self) -> None:
            await super().pre_compute()
            if exchange_manager is None or exchange_manager.trader is None:
                raise octobot_commons.errors.DSLInterpreterError(
                    "exchange_manager and exchange_manager.trader are required for fetch_order operator"
                )
            param_by_name = self.get_computed_value_by_parameter()
            symbol = param_by_name.get("symbol")
            exchange_order_id = param_by_name.get("exchange_order_id")
            if not symbol or not exchange_order_id:
                raise octobot_commons.errors.DSLInterpreterError(
                    "symbol and exchange_order_id are required for fetch_order operator"
                )
            if exchange_manager.is_trader_simulated:
                self.value = _resolve_simulated_fetch_order_dict(
                    exchange_manager, symbol, exchange_order_id
                )
            else:
                self.value = await _resolve_real_trading_fetch_order_dict(
                    exchange_manager, symbol, exchange_order_id
                )

    return [
        _FetchOrderOperator,
    ]
