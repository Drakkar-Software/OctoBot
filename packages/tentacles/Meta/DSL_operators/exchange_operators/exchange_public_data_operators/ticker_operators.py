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

import octobot_commons.constants
import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


TICKER_CLOSE_KEY = "close"
TICKER_OPEN_KEY = "open"
TICKER_HIGH_KEY = "high"
TICKER_LOW_KEY = "low"
TICKER_BASE_VOLUME_KEY = "baseVolume"
TICKER_LAST_KEY = "last"


def create_ticker_operators(
    tickers_by_symbol: dict[str, dict],
) -> list[type[exchange_operator.ExchangeOperator]]:

    class _TickerOperator(exchange_operator.ExchangeOperator):
        TICKER_FIELD: str = ""

        @staticmethod
        def get_library() -> str:
            return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(
                    name="symbol", description="The symbol to get the ticker value for",
                    required=True, type=str,
                ),
            ]

        async def pre_compute(self) -> None:
            await super().pre_compute()
            symbol = self.get_computed_parameters()[0]
            ticker = tickers_by_symbol.get(str(symbol))
            if ticker is None:
                raise octobot_commons.errors.DSLInterpreterError(
                    f"No ticker data available for symbol '{symbol}'"
                )
            value = ticker.get(self.TICKER_FIELD)
            if value is None:
                raise octobot_commons.errors.DSLInterpreterError(
                    f"Ticker field '{self.TICKER_FIELD}' is None for symbol '{symbol}'"
                )
            self.value = value

    class _TickerCloseOperator(_TickerOperator):
        DESCRIPTION = "Returns the close price from the latest fetched ticker"
        EXAMPLE = "ticker_close(triggered_symbol())"
        TICKER_FIELD = TICKER_CLOSE_KEY

        @staticmethod
        def get_name() -> str:
            return "ticker_close"

    class _TickerOpenOperator(_TickerOperator):
        DESCRIPTION = "Returns the open price from the latest fetched ticker"
        EXAMPLE = "ticker_open(triggered_symbol())"
        TICKER_FIELD = TICKER_OPEN_KEY

        @staticmethod
        def get_name() -> str:
            return "ticker_open"

    class _TickerHighOperator(_TickerOperator):
        DESCRIPTION = "Returns the high price from the latest fetched ticker"
        EXAMPLE = "ticker_high(triggered_symbol())"
        TICKER_FIELD = TICKER_HIGH_KEY

        @staticmethod
        def get_name() -> str:
            return "ticker_high"

    class _TickerLowOperator(_TickerOperator):
        DESCRIPTION = "Returns the low price from the latest fetched ticker"
        EXAMPLE = "ticker_low(triggered_symbol())"
        TICKER_FIELD = TICKER_LOW_KEY

        @staticmethod
        def get_name() -> str:
            return "ticker_low"

    class _TickerVolumeOperator(_TickerOperator):
        DESCRIPTION = "Returns the base volume from the latest fetched ticker"
        EXAMPLE = "ticker_volume(triggered_symbol())"
        TICKER_FIELD = TICKER_BASE_VOLUME_KEY

        @staticmethod
        def get_name() -> str:
            return "ticker_volume"

    class _TickerLastOperator(_TickerOperator):
        DESCRIPTION = "Returns the last price from the latest fetched ticker"
        EXAMPLE = "ticker_last(triggered_symbol())"
        TICKER_FIELD = TICKER_LAST_KEY

        @staticmethod
        def get_name() -> str:
            return "ticker_last"

    return [
        _TickerCloseOperator,
        _TickerOpenOperator,
        _TickerHighOperator,
        _TickerLowOperator,
        _TickerVolumeOperator,
        _TickerLastOperator,
    ]
