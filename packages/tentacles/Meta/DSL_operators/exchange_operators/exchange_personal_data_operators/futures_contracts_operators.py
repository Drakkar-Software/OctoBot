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

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


class FuturesContractsOperator(exchange_operator.ExchangeOperator):
    @staticmethod
    def get_library() -> str:
        # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
        return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY
    

def create_futures_contracts_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
) -> typing.List[type[FuturesContractsOperator]]:

    class _SetLeverageOperator(FuturesContractsOperator):
        DESCRIPTION = "Sets the leverage for the futures contract"
        EXAMPLE = "set_leverage('BTC/USDT:USDT', 10)"

        @staticmethod
        def get_name() -> str:
            return "set_leverage"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(name="symbol", description="the symbol of the futures contract", required=True, type=str),
                dsl_interpreter.OperatorParameter(name="leverage", description="the leverage to set", required=True, type=float),
            ]

        async def pre_compute(self) -> None:
            await super().pre_compute()
            if exchange_manager is None:
                raise octobot_commons.errors.DSLInterpreterError(
                    "exchange_manager is required for set_leverage operator"
                )
            param_by_name = self.get_computed_value_by_parameter()
            leverage = decimal.Decimal(str(param_by_name["leverage"]))
            await exchange_manager.trader.set_leverage(
                param_by_name["symbol"],
                None,
                leverage,
            )
            self.value = float(leverage)


    return [_SetLeverageOperator]
