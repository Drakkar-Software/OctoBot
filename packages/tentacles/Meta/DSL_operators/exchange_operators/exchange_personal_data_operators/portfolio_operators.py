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
import dataclasses
import decimal

import octobot_commons.dataclasses
import octobot_commons.constants
import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.personal_data
import octobot_trading.exchanges
import octobot_trading.api

import tentacles.Meta.DSL_operators.exchange_operators.exchange_operator as exchange_operator


CREATED_WITHDRAWALS_KEY = "created_withdrawals"


@dataclasses.dataclass
class WithdrawFundsParams(octobot_commons.dataclasses.FlexibleDataclass):
    asset: str
    network: str # network to withdraw to
    address: str # recipient address of the withdrawal
    amount: typing.Optional[float] = None # defaults to all available balance if unspecified
    tag: str = ""
    params: dict = dataclasses.field(default_factory=dict) # extra parameters specific to the exchange API endpoint


class PortfolioOperator(exchange_operator.ExchangeOperator):
    @staticmethod
    def get_library() -> str:
        # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
        return octobot_commons.constants.CONTEXTUAL_OPERATORS_LIBRARY

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="asset", description="the asset to get the value for", required=False, type=str),
        ]
    

def create_portfolio_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
) -> typing.List[type[PortfolioOperator]]:

    def _get_asset_holdings(asset: str) -> octobot_trading.personal_data.Asset:
        if exchange_manager is None:
            raise octobot_commons.errors.DSLInterpreterError(
                "exchange_manager is required for portfolio operators"
            )
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

    class _WithdrawOperator(PortfolioOperator):
        DESCRIPTION = "Withdraws an asset from the exchange's portfolio. requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)"
        EXAMPLE = "withdraw('BTC', 'ethereum', '0x1234567890abcdef1234567890abcdef12345678', 0.1)"

        @staticmethod
        def get_name() -> str:
            return "withdraw"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(name="asset", description="the asset to withdraw", required=True, type=str),
                dsl_interpreter.OperatorParameter(name="network", description="the network to withdraw to", required=True, type=str),
                dsl_interpreter.OperatorParameter(name="address", description="the address to withdraw to", required=True, type=str),
                dsl_interpreter.OperatorParameter(name="amount", description="the amount to withdraw", required=False, type=float, default=None),
                dsl_interpreter.OperatorParameter(name="tag", description="a tag to associate with the withdrawal", required=False, type=str, default=None),
                dsl_interpreter.OperatorParameter(name="params", description="extra parameters specific to the exchange API endpoint", required=False, type=dict),
            ]
            

        async def pre_compute(self) -> None:
            await super().pre_compute()
            if exchange_manager is None:
                raise octobot_commons.errors.DSLInterpreterError(
                    "exchange_manager is required for withdraw operator"
                )
            param_by_name = self.get_computed_value_by_parameter()
            withdraw_funds_params = WithdrawFundsParams.from_dict(param_by_name)
            amount = withdraw_funds_params.amount or (
                octobot_trading.api.get_portfolio_currency(exchange_manager, withdraw_funds_params.asset).available
            )
            created_withdrawal = await exchange_manager.trader.withdraw(
                withdraw_funds_params.asset,
                decimal.Decimal(str(amount)),
                withdraw_funds_params.network,
                withdraw_funds_params.address,
                tag=withdraw_funds_params.tag,
                params=withdraw_funds_params.params
            )
            self.value = {CREATED_WITHDRAWALS_KEY: [created_withdrawal]}

    return [_TotalOperator, _AvailableOperator, _WithdrawOperator]
