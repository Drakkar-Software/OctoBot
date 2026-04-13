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
import json
import typing
import time

import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors as commons_errors

import octobot_commons.symbols.symbol_util as symbol_util

import octobot_trading.dsl as trading_dsl
import octobot_trading.exchanges
import octobot_trading.modes

import octobot_copy.copiers
import octobot_copy.entities
import octobot_copy.constants

import tentacles.Meta.DSL_operators.exchange_operators.exchange_personal_data_operators.create_order_operators as create_order_operators


def create_copy_exchange_account_operators(
    copier_exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager] = None,
    copier_trading_mode: typing.Optional[octobot_trading.modes.AbstractTradingMode] = None,
) -> list[type[dsl_interpreter.PreComputingCallOperator]]:
    class _CopyExchangeAccountOperator(dsl_interpreter.PreComputingCallOperator, dsl_interpreter.ReCallableOperatorMixin):
        DESCRIPTION = (
            "Rebalances the copier exchange toward the reference account allocation. "
            "reference_account is JSON for octobot_copy.entities.Account (portfolio content, orders, positions). "
            "account_copy_settings is optional JSON for AccountCopySettings; "
            "reference market comes from the copier portfolio."
        )
        EXAMPLE = (
            r"""copy_exchange_account(reference_account='{"content":{"BTC":{"available":"0.01","total":"0.01"}}}', """
            r"""account_copy_settings='{"reference_market_ratio":"1","allow_skip_asset":false}')"""
        )

        @staticmethod
        def get_library() -> str:
            return commons_constants.CONTEXTUAL_OPERATORS_LIBRARY

        @staticmethod
        def get_name() -> str:
            return "copy_exchange_account"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(
                    name="reference_market",
                    description="Quote asset symbol for rebalance (e.g. USDT).",
                    required=True,
                    type=str,
                ),
                dsl_interpreter.OperatorParameter(
                    name="reference_account",
                    description=(
                        "JSON string for Account: fields content (asset -> available/total amounts), "
                        "optional orders and positions lists."
                    ),
                    required=True,
                    type=str,
                ),
                dsl_interpreter.OperatorParameter(
                    name="account_copy_settings",
                    description=(
                        "JSON string for AccountCopySettings: optional keys "
                        "synchronization_policy, rebalance_trigger_min_ratio, "
                        "quote_asset_rebalance_ratio_threshold, reference_market_ratio, "
                        "sell_untargeted_traded_coins, min_order_size_margin, allow_skip_asset "
                        "(omit keys to use defaults)."
                    ),
                    required=False,
                    type=str,
                ),
            ] + super().get_re_callable_parameters()

        def _parse_reference_account(self, raw: typing.Any) -> octobot_copy.entities.Account:
            if raw is None:
                raise commons_errors.InvalidParameterFormatError("reference_account is required")
            if isinstance(raw, dict):
                payload = raw
            elif isinstance(raw, str):
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError as err:
                    raise commons_errors.InvalidParameterFormatError(
                        f"Invalid reference_account JSON: {err}"
                    ) from err
            else:
                raise commons_errors.InvalidParameterFormatError(
                    f"reference_account must be a JSON string or object, got {type(raw).__name__}"
                )
            if not isinstance(payload, dict):
                raise commons_errors.InvalidParameterFormatError(
                    "reference_account JSON must deserialize to an object"
                )
            return octobot_copy.entities.Account.from_dict(payload)

        def _parse_account_copy_settings(self, raw: typing.Any) -> octobot_copy.entities.AccountCopySettings:
            if raw is None:
                return octobot_copy.entities.AccountCopySettings()
            if isinstance(raw, dict):
                return octobot_copy.entities.AccountCopySettings.from_dict(raw)
            if not isinstance(raw, str):
                raise commons_errors.InvalidParameterFormatError(
                    f"account_copy_settings must be a JSON string, got {type(raw).__name__}"
                )
            try:
                return octobot_copy.entities.AccountCopySettings.from_dict(json.loads(raw))
            except json.JSONDecodeError as err:
                raise commons_errors.InvalidParameterFormatError(
                    f"Invalid account_copy_settings JSON: {err}"
                ) from err

        def get_dependencies(self) -> list[dsl_interpreter.InterpreterDependency]:
            dependencies = super().get_dependencies()
            params = self.get_computed_value_by_parameter()
            ref_market = params.get("reference_market")
            try:
                account = self._parse_reference_account(params.get("reference_account"))
            except commons_errors.InvalidParameterFormatError:
                return dependencies
            seen: set[str] = set()
            for asset in account.content:
                if asset == ref_market:
                    continue
                symbol = symbol_util.merge_currencies(asset, ref_market)
                if symbol not in seen:
                    seen.add(symbol)
                    dependencies.append(trading_dsl.SymbolDependency(symbol=symbol))
            return dependencies

        async def pre_compute(self) -> None:
            await super().pre_compute()
            execution_time = time.time()
            if copier_exchange_manager is None:
                raise commons_errors.DSLInterpreterError(
                    "copier_exchange_manager is required in context to execute copy_exchange_account"
                )
            params = self.get_computed_value_by_parameter()
            reference_account = self._parse_reference_account(params.get("reference_account"))
            copy_settings = self._parse_account_copy_settings(params.get("account_copy_settings"))
            account_copier = octobot_copy.copiers.create_account_copier(
                reference_account,
                copy_settings,
                copier_exchange_manager,
                copier_trading_mode,
            )
            copy_result = await account_copier.copy_account()
            self.value = self.create_re_callable_result_dict(
                keyword=self.get_name(),
                waiting_time=octobot_copy.constants.DEFAULT_COPY_WAITING_TIME,
                last_execution_time=execution_time,
                state={
                    create_order_operators.CREATED_ORDERS_KEY: [
                        order.to_dict() for order in copy_result.created_orders
                    ],
                },
            )

    return [_CopyExchangeAccountOperator]


__all__ = ["create_copy_exchange_account_operators"]
