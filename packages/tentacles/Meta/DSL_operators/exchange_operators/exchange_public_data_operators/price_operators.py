# pylint: disable=missing-class-docstring,missing-function-docstring
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
import decimal

import octobot_commons.constants
import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.exchanges
import octobot_trading.api
import octobot_trading.constants

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator
import tentacles.Meta.DSL_operators.exchange_operators.exchange_public_data_operators.ohlcv_operators as ohlcv_operators


class PriceOperator(exchange_operator.ExchangeOperator):
    @staticmethod
    def get_library() -> str:
        # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
        return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(
                name="symbol",
                description="the symbol to get the latest mark price for",
                required=False,
                type=str,
            ),
        ]

    def get_symbol(self) -> typing.Optional[str]:
        if parameters := self.get_computed_parameters():
            symbol = parameters[0] if len(parameters) > 0 else None
            return str(symbol) if symbol is not None else None
        return None


def create_price_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
    symbol: typing.Optional[str],
    price_by_symbol: typing.Optional[dict[str, typing.Optional[decimal.Decimal]]] = None
) -> typing.List[type[PriceOperator]]:

    def _get_latest_price(input_symbol: typing.Optional[str]) -> float:
        if exchange_manager is None:
            if price_by_symbol:
                if input_symbol in price_by_symbol:
                    return float(price_by_symbol[input_symbol])
                raise octobot_commons.errors.DSLInterpreterError(
                    f"Price for symbol {input_symbol} not found in price_by_symbol: {price_by_symbol}"
                )
            raise octobot_commons.errors.DSLInterpreterError(
                "exchange_manager must be provided"
            )
        resolved_symbol = exchange_manager.get_exchange_symbol(input_symbol or symbol)
        try:
            symbol_data = octobot_trading.api.get_symbol_data(
                exchange_manager, resolved_symbol, allow_creation=False
            )
            mark_price = symbol_data.prices_manager.get_mark_price_no_wait()
        except KeyError:
            raise octobot_commons.errors.DSLInterpreterError(
                f"No symbol data found for {resolved_symbol} on {exchange_manager.exchange_name}"
            )
        except ValueError as err:
            raise octobot_commons.errors.DSLInterpreterError(
                f"No up to date mark price for {resolved_symbol} on {exchange_manager.exchange_name}"
            ) from err
        return float(mark_price)

    def _static_get_dependencies() -> typing.List[ohlcv_operators.ExchangeDataDependency]:
        return [
            ohlcv_operators.ExchangeDataDependency(
                symbol=symbol,
                time_frame=None,
                data_source=octobot_trading.constants.MARK_PRICE_CHANNEL,
            )
        ] if symbol else []

    class _LocalPriceOperator(PriceOperator):
        DESCRIPTION = "Returns the latest mark price for the symbol"
        EXAMPLE = "price('BTC/USDT')"

        @staticmethod
        def get_name() -> str:
            return "price"

        def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
            local_dependencies = _static_get_dependencies()
            param_by_name = self.get_input_value_by_parameter()
            if param_symbol := param_by_name.get("symbol"):
                symbol_dep = ohlcv_operators.ExchangeDataDependency(
                    symbol=param_symbol,
                    time_frame=None,
                    data_source=octobot_trading.constants.MARK_PRICE_CHANNEL,
                )
                if symbol_dep not in local_dependencies:
                    local_dependencies.append(symbol_dep)
            for dependency in local_dependencies:
                dependency.resolve_symbol(exchange_manager)
            return super().get_dependencies() + local_dependencies

        async def pre_compute(self) -> None:
            await super().pre_compute()
            self.value = _get_latest_price(self.get_symbol())

    return [_LocalPriceOperator]
