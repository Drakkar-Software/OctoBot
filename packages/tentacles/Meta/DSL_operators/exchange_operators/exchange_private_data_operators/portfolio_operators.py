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
import octobot_trading.personal_data
import octobot_trading.exchanges
import octobot_trading.api

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


class PortfolioOperator(exchange_operator.ExchangeOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.value: dsl_interpreter_operator.ComputedOperatorParameterType = exchange_operator.UNINITIALIZED_VALUE # type: ignore

    @staticmethod
    def get_library() -> str:
        # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
        return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

    @staticmethod
    def get_parameters() -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="asset", description="the asset to get the value for", required=False, type=str),
        ]

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        if self.value is exchange_operator.UNINITIALIZED_VALUE:
            raise octobot_commons.errors.DSLInterpreterError("{self.__class__.__name__} has not been initialized")
        return self.value


def create_portfolio_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
) -> typing.List[type[PortfolioOperator]]:

    def _get_asset_holdings(asset: str) -> octobot_trading.personal_data.Asset:
        return octobot_trading.api.get_portfolio_currency(exchange_manager, asset)

    class _TotalOperator(PortfolioOperator):
        DESCRIPTION = "Returns the total holdings of the asset in the portfolio"
        EXAMPLE = "total('BTC')"

        @staticmethod
        def get_name() -> str:
            return "total"

        async def pre_compute(self) -> None:
            await super().pre_compute()
            asset = self.get_computed_parameters()[0]
            self.value = float(_get_asset_holdings(asset).total)

    class _AvailableOperator(PortfolioOperator):
        DESCRIPTION = "Returns the available holdings of the asset in the portfolio"
        EXAMPLE = "available('BTC')"

        @staticmethod
        def get_name() -> str:
            return "available"

        async def pre_compute(self) -> None:
            await super().pre_compute()
            asset = self.get_computed_parameters()[0]
            self.value = float(_get_asset_holdings(asset).available)
        

    return [_TotalOperator, _AvailableOperator]
