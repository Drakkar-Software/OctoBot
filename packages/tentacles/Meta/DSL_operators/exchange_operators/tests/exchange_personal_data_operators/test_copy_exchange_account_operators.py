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

import mock
import pytest
import pytest_asyncio

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.dsl_interpreter.operators.re_callable_operator_mixin as re_callable_operator_mixin
import octobot_trading.dsl

import octobot_copy.copiers.account_copier as account_copier_module
import octobot_copy.entities as copy_entities

import tentacles.Meta.DSL_operators.exchange_operators.exchange_personal_data_operators.copy_exchange_account_operators as copy_exchange_account_operators

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    backtesting_config,
    fake_backtesting,
    backtesting_exchange_manager,
    backtesting_trader,
)


STRATEGY_ID = "test-copy-strategy-id"
REFERENCE_MARKET = "USDT"
REFERENCE_ACCOUNT_JSON = json.dumps(
    {
        "version": "1.0.0",
        "updated_at": 1710000000.0,
        "copied_assets": [
            {"name": "BTC", "total": 0.01, "available": 0.01, "ratio": 1.0},
        ],
    },
    separators=(",", ":"),
)


@pytest.fixture
def copy_exchange_interpreter():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + copy_exchange_account_operators.create_copy_exchange_account_operators(None)
    )


@pytest_asyncio.fixture
async def copy_exchange_interpreter_with_exchange_manager(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + copy_exchange_account_operators.create_copy_exchange_account_operators(exchange_manager)
    )


class TestCreateCopyExchangeAccountOperators:
    def test_returns_single_operator_class(self):
        operator_classes = copy_exchange_account_operators.create_copy_exchange_account_operators(None)
        assert len(operator_classes) == 1
        assert operator_classes[0].get_name() == "copy_exchange_account"


class TestGetName:
    def test_operator_name(self):
        operator_class = copy_exchange_account_operators.create_copy_exchange_account_operators(None)[0]
        assert operator_class.get_name() == "copy_exchange_account"


class TestGetParameters:
    def test_strategy_id_is_first_and_required(self):
        operator_class = copy_exchange_account_operators.create_copy_exchange_account_operators(None)[0]
        parameters = operator_class.get_parameters()
        strategy_parameter = parameters[0]
        assert strategy_parameter.name == "strategy_id"
        assert strategy_parameter.required is True


class TestGetDependencies:
    def test_includes_copy_trading_and_symbol_dependencies(self, copy_exchange_interpreter):
        dsl_expression = (
            f"copy_exchange_account(strategy_id='{STRATEGY_ID}', reference_market='{REFERENCE_MARKET}', "
            f"reference_account='{REFERENCE_ACCOUNT_JSON}', account_copy_settings='{{}}')"
        )
        copy_exchange_interpreter.prepare(dsl_expression)
        dependencies = copy_exchange_interpreter.get_dependencies()
        # Parsed reference account is present: no refresh needed to fetch it
        assert octobot_trading.dsl.CopyTradingDependency(strategy_id=STRATEGY_ID, refresh_required=False) in dependencies
        assert octobot_trading.dsl.SymbolDependency(symbol="BTC/USDT") in dependencies

    def test_invalid_reference_account_skips_symbol_dependencies(self, copy_exchange_interpreter):
        dsl_expression = (
            f"copy_exchange_account(strategy_id='{STRATEGY_ID}', reference_market='{REFERENCE_MARKET}', "
            f"reference_account='not-json', account_copy_settings='{{}}')"
        )
        copy_exchange_interpreter.prepare(dsl_expression)
        dependencies = copy_exchange_interpreter.get_dependencies()
        # Parse failed: refresh required to obtain reference account data
        assert octobot_trading.dsl.CopyTradingDependency(strategy_id=STRATEGY_ID, refresh_required=True) in dependencies
        assert not any(
            isinstance(dependency, octobot_trading.dsl.SymbolDependency)
            for dependency in dependencies
        )


class TestCopyExchangeAccountCallAsDsl:
    @pytest.mark.asyncio
    async def test_copy_exchange_account_call_as_dsl(
        self, copy_exchange_interpreter_with_exchange_manager, backtesting_trader
    ):
        _config, _exchange_manager, _trader = backtesting_trader
        account_copy_result = copy_entities.AccountCopyResult(created_orders=[])

        dsl_expression = (
            f"copy_exchange_account(strategy_id='{STRATEGY_ID}', reference_market='{REFERENCE_MARKET}', "
            f"reference_account='{REFERENCE_ACCOUNT_JSON}', account_copy_settings='{{}}')"
        )

        with mock.patch.object(
            account_copier_module.AccountCopier,
            "copy_account",
            mock.AsyncMock(return_value=account_copy_result),
        ) as copy_account_mock:
            result = await copy_exchange_interpreter_with_exchange_manager.interprete(dsl_expression)

        copy_account_mock.assert_awaited_once()

        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result(result)
        re_calling_payload = result[re_callable_operator_mixin.ReCallingOperatorResult.__name__]
        assert re_calling_payload["keyword"] == "copy_exchange_account"
        last_execution_state = re_calling_payload["last_execution_result"]["state"]
        assert last_execution_state["created_orders"] == []
