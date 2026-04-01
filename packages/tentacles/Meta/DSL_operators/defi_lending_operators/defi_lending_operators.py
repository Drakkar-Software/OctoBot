#  Drakkar-Software OctoBot-Tentacles
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

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.exchanges


DEFI_LENDING_LIBRARY = "defi_lending"


class DeFiLendingOperator(dsl_interpreter.PreComputingCallOperator):
    @staticmethod
    def get_library() -> str:
        return DEFI_LENDING_LIBRARY


def create_defi_lending_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
) -> typing.List[type[DeFiLendingOperator]]:
    """
    Factory function that creates and returns DeFi lending DSL operator classes.
    Follows the same pattern as create_blockchain_wallet_operators().

    TODO: To register these operators, add the following call to
    packages/flow/octobot_flow/logic/dsl/dsl_executor.py in _create_interpreter():
        + dsl_operators.create_defi_lending_operators(self._exchange_manager)
    """

    class _LendingHealthFactorOperator(DeFiLendingOperator):
        DESCRIPTION = (
            "Returns the health factor of a user's position on a lending protocol. "
            "Health factor < 1.0 means the position is liquidatable."
        )
        EXAMPLE = "lending_health_factor('aave_v3_polygon', '0x1234...')"

        @staticmethod
        def get_name() -> str:
            return "lending_health_factor"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(
                    name="protocol_name",
                    description="the lending protocol to query (e.g., 'aave_v3_polygon')",
                    required=True,
                    type=str,
                ),
                dsl_interpreter.OperatorParameter(
                    name="user_address",
                    description="the blockchain address of the user to query",
                    required=True,
                    type=str,
                ),
            ]

        async def pre_compute(self) -> None:
            """
            TODO: Implement:
            1. param_by_name = self.get_computed_value_by_parameter()
            2. protocol_name = param_by_name["protocol_name"]
            3. user_address = param_by_name["user_address"]
            4. Create wallet and protocol instances
            5. position = await protocol.get_user_account_data(user_address)
            6. self.value = float(position.health_factor)
            """
            raise NotImplementedError(
                "lending_health_factor operator is not yet implemented"
            )

    class _LendingLiquidatableCountOperator(DeFiLendingOperator):
        DESCRIPTION = (
            "Returns the number of liquidatable positions on a lending protocol "
            "with debt above the specified minimum USD threshold."
        )
        EXAMPLE = "lending_liquidatable_count('aave_v3_polygon', 100.0)"

        @staticmethod
        def get_name() -> str:
            return "lending_liquidatable_count"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(
                    name="protocol_name",
                    description="the lending protocol to query (e.g., 'aave_v3_polygon')",
                    required=True,
                    type=str,
                ),
                dsl_interpreter.OperatorParameter(
                    name="min_debt_usd",
                    description="minimum debt value in USD to consider",
                    required=False,
                    type=float,
                    default=0.0,
                ),
            ]

        async def pre_compute(self) -> None:
            """
            TODO: Implement:
            1. param_by_name = self.get_computed_value_by_parameter()
            2. protocol_name = param_by_name["protocol_name"]
            3. min_debt = Decimal(str(param_by_name.get("min_debt_usd", 0)))
            4. Create wallet and protocol instances
            5. positions = await protocol.get_liquidatable_positions(min_debt)
            6. self.value = len(positions)
            """
            raise NotImplementedError(
                "lending_liquidatable_count operator is not yet implemented"
            )

    return [_LendingHealthFactorOperator, _LendingLiquidatableCountOperator]
