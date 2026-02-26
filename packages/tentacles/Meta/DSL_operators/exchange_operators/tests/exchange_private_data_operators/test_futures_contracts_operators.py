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
import mock
import pytest
import pytest_asyncio

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter

import tentacles.Meta.DSL_operators.exchange_operators.exchange_private_data_operators.futures_contracts_operators as futures_contracts_operators

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    backtesting_config,
    fake_backtesting,
    backtesting_exchange_manager,
    backtesting_trader,
)

FUTURES_SYMBOL = "BTC/USDT:USDT"
LEVERAGE = 10


@pytest_asyncio.fixture
async def futures_contracts_operators_list(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    return futures_contracts_operators.create_futures_contracts_operators(exchange_manager)


@pytest_asyncio.fixture
async def interpreter(futures_contracts_operators_list):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + futures_contracts_operators_list
    )


class TestSetLeverageOperator:
    @pytest.mark.asyncio
    async def test_pre_compute_sets_leverage(self, futures_contracts_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        set_leverage_op_class, = futures_contracts_operators_list

        with mock.patch.object(
            _trader,
            "set_leverage",
            mock.AsyncMock(return_value=True),
        ) as set_leverage_mock:
            operator = set_leverage_op_class(FUTURES_SYMBOL, LEVERAGE)
            await operator.pre_compute()

            assert operator.value == float(LEVERAGE)
            set_leverage_mock.assert_awaited_once_with(
                FUTURES_SYMBOL,
                None,
                mock.ANY,
            )
            call_args = set_leverage_mock.call_args
            assert float(call_args[0][2]) == LEVERAGE

    @pytest.mark.asyncio
    async def test_pre_compute_with_float_leverage(self, futures_contracts_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        set_leverage_op_class, = futures_contracts_operators_list

        leverage_value = 5.5
        with mock.patch.object(
            _trader,
            "set_leverage",
            mock.AsyncMock(return_value=True),
        ) as set_leverage_mock:
            operator = set_leverage_op_class(FUTURES_SYMBOL, leverage_value)
            await operator.pre_compute()

            assert operator.value == leverage_value
            set_leverage_mock.assert_awaited_once()

    def test_compute_without_pre_compute(self, futures_contracts_operators_list):
        set_leverage_op_class, = futures_contracts_operators_list
        operator = set_leverage_op_class(FUTURES_SYMBOL, LEVERAGE)
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="has not been pre_computed",
        ):
            operator.compute()

    @pytest.mark.asyncio
    async def test_set_leverage_call_as_dsl(self, interpreter, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader

        with mock.patch.object(
            _trader,
            "set_leverage",
            mock.AsyncMock(return_value=True),
        ) as set_leverage_mock:
            result = await interpreter.interprete(
                f"set_leverage('{FUTURES_SYMBOL}', {LEVERAGE})"
            )
            assert result == float(LEVERAGE)
            set_leverage_mock.assert_awaited_once_with(
                FUTURES_SYMBOL,
                None,
                mock.ANY,
            )

    @pytest.mark.asyncio
    async def test_set_leverage_call_as_dsl_with_leverage_param(self, interpreter, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader

        with mock.patch.object(
            _trader,
            "set_leverage",
            mock.AsyncMock(return_value=True),
        ) as set_leverage_mock:
            result = await interpreter.interprete(
                f"set_leverage('{FUTURES_SYMBOL}', leverage={LEVERAGE})"
            )
            assert result == float(LEVERAGE)
            set_leverage_mock.assert_awaited_once()
