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

import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.enums as trading_enums

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


class _SymbolOperatorHost(typing.Protocol):
    triggered_symbol: str
    exchange_manager: typing.Any


def create_symbol_operators(
    host: _SymbolOperatorHost,
) -> list[type[exchange_operator.ExchangeOperator]]:
    return [
        _triggered_symbol_operator(host),
        _market_expiry_operator(host),
    ]


def _triggered_symbol_operator(
    host: _SymbolOperatorHost,
) -> type[exchange_operator.ExchangeOperator]:
    class _TriggeredSymbolOperator(exchange_operator.ExchangeOperator):
        DESCRIPTION = "Returns the symbol that triggered the current DSL execution"
        EXAMPLE = "triggered_symbol()"

        @staticmethod
        def get_library() -> str:
            return commons_constants.CONTEXTUAL_OPERATORS_LIBRARY

        @classmethod
        def get_parameters(cls) -> list:
            return []

        @staticmethod
        def get_name() -> str:
            return "triggered_symbol"

        async def pre_compute(self) -> None:
            await super().pre_compute()
            self.value = host.triggered_symbol

    return _TriggeredSymbolOperator


def _market_expiry_operator(
    host: _SymbolOperatorHost,
) -> type[exchange_operator.ExchangeOperator]:
    class _MarketExpiryOperator(exchange_operator.ExchangeOperator):
        DESCRIPTION = "Returns the expiry timestamp in milliseconds for the given symbol's market, or None"
        EXAMPLE = "market_expiry(triggered_symbol())"

        @classmethod
        def get_parameters(cls) -> list:
            return [dsl_interpreter.OperatorParameter("symbol", "The market symbol", True, str)]

        @staticmethod
        def get_name() -> str:
            return "market_expiry"

        async def pre_compute(self) -> None:
            await super().pre_compute()
            symbol = self.get_computed_parameters()[0]
            markets = host.exchange_manager.exchange.connector.client.markets or {}
            self.value = (markets.get(symbol) or {}).get(
                trading_enums.ExchangeConstantsMarketStatusColumns.EXPIRY.value
            )

    return _MarketExpiryOperator
