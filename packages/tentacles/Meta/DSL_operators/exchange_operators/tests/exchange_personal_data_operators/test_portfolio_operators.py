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
import decimal
import mock
import octobot_commons.constants as commons_constants
import pytest
import pytest_asyncio

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants

import tentacles.Meta.DSL_operators.exchange_operators.exchange_personal_data_operators.portfolio_operators as portfolio_operators

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    backtesting_config,
    fake_backtesting,
    backtesting_exchange_manager,
    backtesting_trader,
)

ASSET_BTC = "BTC"
ASSET_USDT = "USDT"
ASSET_ETH = "ETH"


def _ensure_portfolio_config(backtesting_trader, portfolio_content):
    _config, exchange_manager, _trader = backtesting_trader
    if commons_constants.CONFIG_SIMULATOR not in _config:
        _config[commons_constants.CONFIG_SIMULATOR] = {}
    if commons_constants.CONFIG_STARTING_PORTFOLIO not in _config[commons_constants.CONFIG_SIMULATOR]:
        _config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO] = {}
    _config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO].update(
        portfolio_content
    )
    exchange_manager.exchange_personal_data.portfolio_manager.apply_forced_portfolio(
        _config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]
    )


@pytest_asyncio.fixture
async def portfolio_operators_list(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    return portfolio_operators.create_portfolio_operators(exchange_manager)


@pytest_asyncio.fixture
async def interpreter(portfolio_operators_list):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + portfolio_operators_list
    )


class TestTotalOperator:
    @pytest.mark.asyncio
    async def test_pre_compute(self, portfolio_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        total_op_class, _, _ = portfolio_operators_list

        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 1.5, ASSET_USDT: 1000})

        operator = total_op_class(ASSET_BTC)
        await operator.pre_compute()
        assert operator.value == 1.5

    @pytest.mark.asyncio
    async def test_pre_compute_asset_not_in_portfolio(self, portfolio_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        total_op_class, _, _ = portfolio_operators_list

        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 1.5, ASSET_USDT: 1000})

        operator = total_op_class(ASSET_ETH)
        await operator.pre_compute()
        assert operator.value == float(octobot_trading.constants.ZERO)

    def test_compute_without_pre_compute(self, portfolio_operators_list):
        total_op_class, _, _ = portfolio_operators_list
        operator = total_op_class(ASSET_BTC)
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="has not been pre_computed",
        ):
            operator.compute()

    @pytest.mark.asyncio
    async def test_total_call_as_dsl(self, interpreter, backtesting_trader):
        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 2.0, ASSET_USDT: 500})

        assert await interpreter.interprete(f"total('{ASSET_BTC}')") == 2.0
        assert await interpreter.interprete(f"total('{ASSET_USDT}')") == 500.0
        assert await interpreter.interprete(f"total('{ASSET_ETH}')") == 0.0


class TestAvailableOperator:
    @pytest.mark.asyncio
    async def test_pre_compute(self, portfolio_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        _, available_op_class, _ = portfolio_operators_list

        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 1.5, ASSET_USDT: 1000})

        operator = available_op_class(ASSET_BTC)
        await operator.pre_compute()
        assert operator.value == 1.5

    @pytest.mark.asyncio
    async def test_pre_compute_asset_not_in_portfolio(self, portfolio_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        _, available_op_class, _ = portfolio_operators_list

        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 1.5, ASSET_USDT: 1000})

        operator = available_op_class(ASSET_ETH)
        await operator.pre_compute()
        assert operator.value == float(octobot_trading.constants.ZERO)

    def test_compute_without_pre_compute(self, portfolio_operators_list):
        _, available_op_class, _ = portfolio_operators_list
        operator = available_op_class(ASSET_BTC)
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="has not been pre_computed",
        ):
            operator.compute()

    @pytest.mark.asyncio
    async def test_available_call_as_dsl(self, interpreter, backtesting_trader):
        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 3.0, ASSET_USDT: 2000})

        assert await interpreter.interprete(f"available('{ASSET_BTC}')") == 3.0
        assert await interpreter.interprete(f"available('{ASSET_USDT}')") == 2000.0
        assert await interpreter.interprete(f"available('{ASSET_ETH}')") == 0.0


class TestWithdrawOperator:
    NETWORK = "ethereum"
    ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"
    WITHDRAW_RESULT = {"id": "withdrawal-123", "status": "ok"}

    @pytest.mark.asyncio
    async def test_pre_compute(self, portfolio_operators_list, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        _, _, withdraw_op_class = portfolio_operators_list
        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 1.0, ASSET_USDT: 1000})

        with mock.patch.object(
            exchange_manager.trader,
            "withdraw",
            mock.AsyncMock(return_value=self.WITHDRAW_RESULT),
        ) as withdraw_mock:
            operator = withdraw_op_class(ASSET_BTC, self.NETWORK, self.ADDRESS, 0.1)
            await operator.pre_compute()

        assert operator.value == {"created_withdrawals": [self.WITHDRAW_RESULT]}
        withdraw_mock.assert_awaited_once_with(
            ASSET_BTC,
            decimal.Decimal("0.1"),
            self.NETWORK,
            self.ADDRESS,
            tag=None,
            params={},
        )

    @pytest.mark.asyncio
    async def test_pre_compute_uses_available_balance_when_amount_omitted(
        self, portfolio_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _, _, withdraw_op_class = portfolio_operators_list
        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 0.5, ASSET_USDT: 1000})

        with mock.patch.object(
            exchange_manager.trader,
            "withdraw",
            mock.AsyncMock(return_value=self.WITHDRAW_RESULT),
        ) as withdraw_mock:
            operator = withdraw_op_class(ASSET_BTC, self.NETWORK, self.ADDRESS)
            await operator.pre_compute()

        assert operator.value == {"created_withdrawals": [self.WITHDRAW_RESULT]}
        withdraw_mock.assert_awaited_once_with(
            ASSET_BTC,
            decimal.Decimal("0.5"),
            self.NETWORK,
            self.ADDRESS,
            tag=None,
            params={},
        )

    @pytest.mark.asyncio
    async def test_pre_compute_with_tag_and_params(
        self, portfolio_operators_list, backtesting_trader
    ):
        _config, exchange_manager, _trader = backtesting_trader
        _, _, withdraw_op_class = portfolio_operators_list
        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 1.0})
        tag = "memo-123"
        params = {"fee": "low"}

        with mock.patch.object(
            exchange_manager.trader,
            "withdraw",
            mock.AsyncMock(return_value=self.WITHDRAW_RESULT),
        ) as withdraw_mock:
            operator = withdraw_op_class(
                ASSET_BTC, self.NETWORK, self.ADDRESS, 0.1, tag=tag, params=params
            )
            await operator.pre_compute()

        withdraw_mock.assert_awaited_once_with(
            ASSET_BTC,
            decimal.Decimal("0.1"),
            self.NETWORK,
            self.ADDRESS,
            tag=tag,
            params=params,
        )

    def test_compute_without_pre_compute(self, portfolio_operators_list):
        _, _, withdraw_op_class = portfolio_operators_list
        operator = withdraw_op_class(ASSET_BTC, self.NETWORK, self.ADDRESS, 0.1)
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="has not been pre_computed",
        ):
            operator.compute()

    @pytest.mark.asyncio
    async def test_withdraw_call_as_dsl(self, interpreter, backtesting_trader):
        _config, exchange_manager, _trader = backtesting_trader
        _ensure_portfolio_config(backtesting_trader, {ASSET_BTC: 2.0, ASSET_USDT: 1000})

        with mock.patch.object(
            exchange_manager.trader,
            "withdraw",
            mock.AsyncMock(return_value={"id": "wd-456", "status": "ok"}),
        ) as withdraw_mock:
            result = await interpreter.interprete(
                f"withdraw('{ASSET_BTC}', '{self.NETWORK}', '{self.ADDRESS}', 1.5)"
            )

        assert result == {"created_withdrawals": [{"id": "wd-456", "status": "ok"}]}
        withdraw_mock.assert_awaited_once_with(
            ASSET_BTC,
            decimal.Decimal("1.5"),
            self.NETWORK,
            self.ADDRESS,
            tag=None,
            params={},
        )
