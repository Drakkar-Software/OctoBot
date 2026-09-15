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

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.dsl_interpreter.dictionnaries as dsl_dictionaries
import octobot_commons.errors
import octobot_flow.entities
import octobot_trading.enums

import tentacles.Meta.DSL_operators.automation_operators.automation_management as automation_management


def _assert_stop_automation_result(result):
    assert isinstance(result, dict)
    assert octobot_flow.entities.PostIterationActionsDetails.__name__ in result
    details = octobot_flow.entities.PostIterationActionsDetails.from_dict(
        result[octobot_flow.entities.PostIterationActionsDetails.__name__]
    )
    assert details.stop_automation is True


_SAMPLE_CONFIGURATION_UPDATE_DSL = 'run_octobot_process("u", profile_data={})'


def _assert_update_automation_configuration_result(result, expected_configuration_update: str):
    assert isinstance(result, dict)
    assert octobot_flow.entities.PostIterationActionsDetails.__name__ in result
    details = octobot_flow.entities.PostIterationActionsDetails.from_dict(
        result[octobot_flow.entities.PostIterationActionsDetails.__name__]
    )
    assert details.configuration_update == expected_configuration_update


def _create_mock_order(exchange_order_id: str, side: str = "buy"):
    order = mock.Mock()
    order.exchange_order_id = exchange_order_id
    order.side = octobot_trading.enums.TradeOrderSide(side)
    order.is_cancelled = mock.Mock(return_value=False)
    order.is_closed = mock.Mock(return_value=False)
    return order


def _mock_exchange_manager():
    exchange_manager = mock.Mock()
    exchange_manager.exchange_personal_data.orders_manager.get_open_orders = mock.Mock(return_value=[])
    exchange_manager.trader.cancel_order = mock.AsyncMock(return_value=True)
    return exchange_manager


@pytest.fixture
def interpreter_without_stop_automation():
    dsl_dictionaries.clear_get_all_operators_cache()
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
    )


@pytest.fixture
def stop_automation_operators_list():
    return automation_management.create_stop_automation_operators(_mock_exchange_manager())


@pytest.fixture
def interpreter(stop_automation_operators_list):
    dsl_dictionaries.clear_get_all_operators_cache()
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + stop_automation_operators_list
    )


@pytest.fixture
def no_exchange_manager_stop_automation_operators_list():
    return automation_management.create_stop_automation_operators(None)


@pytest.fixture
def no_exchange_manager_interpreter(no_exchange_manager_stop_automation_operators_list):
    dsl_dictionaries.clear_get_all_operators_cache()
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + no_exchange_manager_stop_automation_operators_list
    )


class TestCreateStopAutomationOperators:
    def test_create_with_none_exchange_manager_returns_operator_class(self):
        operators_list = automation_management.create_stop_automation_operators(None)
        assert len(operators_list) == 1
        assert operators_list[0].get_name() == "stop_automation"


class TestStopAutomationOperator:
    @pytest.mark.asyncio
    async def test_call_as_dsl(self, no_exchange_manager_interpreter):
        assert "stop_automation" in no_exchange_manager_interpreter.operators_by_name

        result = await no_exchange_manager_interpreter.interprete("stop_automation()")
        _assert_stop_automation_result(result)

    @pytest.mark.asyncio
    async def test_call_as_dsl_with_cancel_orders(self, no_exchange_manager_interpreter):
        result = await no_exchange_manager_interpreter.interprete("stop_automation(cancel_orders=True)")
        _assert_stop_automation_result(result)

    def test_compute(self, stop_automation_operators_list):
        stop_automation_op_class, = stop_automation_operators_list
        operator = stop_automation_op_class()
        result = operator.compute()
        _assert_stop_automation_result(result)

    def test_compute_with_cancel_orders_false(self, stop_automation_operators_list):
        stop_automation_op_class, = stop_automation_operators_list
        operator = stop_automation_op_class(cancel_orders=False)
        result = operator.compute()
        _assert_stop_automation_result(result)

    @pytest.mark.asyncio
    async def test_invalid_parameters(self, no_exchange_manager_interpreter):
        with pytest.raises(
            octobot_commons.errors.InvalidParametersError,
            match="supports up to 1",
        ):
            await no_exchange_manager_interpreter.interprete(
                "stop_automation(True, cancel_orders=True)"
            )

    def test_docs(self, stop_automation_operators_list):
        stop_automation_op_class, = stop_automation_operators_list
        docs = stop_automation_op_class.get_docs()
        assert docs.name == "stop_automation"
        assert "stop" in docs.description.lower()
        assert "cancel_orders" in docs.example

    @pytest.mark.asyncio
    async def test_pre_compute_cancel_orders_false_does_not_cancel(self, stop_automation_operators_list):
        stop_automation_op_class, = stop_automation_operators_list
        exchange_manager = _mock_exchange_manager()

        with mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(),
        ) as cancel_order_mock:
            operators_list = automation_management.create_stop_automation_operators(exchange_manager)
            operator = operators_list[0](cancel_orders=False)
            await operator.pre_compute()
            cancel_order_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pre_compute_cancel_orders_true_cancels_open_orders(self):
        exchange_manager = _mock_exchange_manager()
        mock_orders = [_create_mock_order("order-1"), _create_mock_order("order-2", side="sell")]
        exchange_manager.exchange_personal_data.orders_manager.get_open_orders = mock.Mock(
            return_value=mock_orders
        )
        stop_automation_op_class, = automation_management.create_stop_automation_operators(exchange_manager)

        with mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(side_effect=[True, True]),
        ) as cancel_order_mock:
            operator = stop_automation_op_class(cancel_orders=True)
            await operator.pre_compute()
            assert cancel_order_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_pre_compute_cancel_orders_true_no_open_orders(self):
        exchange_manager = _mock_exchange_manager()
        stop_automation_op_class, = automation_management.create_stop_automation_operators(exchange_manager)

        with mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(),
        ) as cancel_order_mock:
            operator = stop_automation_op_class(cancel_orders=True)
            await operator.pre_compute()
            cancel_order_mock.assert_not_awaited()
            _assert_stop_automation_result(operator.compute())

    @pytest.mark.asyncio
    async def test_pre_compute_cancel_orders_true_without_exchange_manager(
        self, no_exchange_manager_stop_automation_operators_list,
    ):
        stop_automation_op_class, = no_exchange_manager_stop_automation_operators_list
        operator = stop_automation_op_class(cancel_orders=True)
        await operator.pre_compute()
        _assert_stop_automation_result(operator.compute())

    @pytest.mark.asyncio
    async def test_pre_compute_skips_cancelled_and_closed_orders(self):
        exchange_manager = _mock_exchange_manager()
        cancelled_order = _create_mock_order("order-cancelled")
        cancelled_order.is_cancelled = mock.Mock(return_value=True)
        closed_order = _create_mock_order("order-closed")
        closed_order.is_closed = mock.Mock(return_value=True)
        active_order = _create_mock_order("order-active")
        exchange_manager.exchange_personal_data.orders_manager.get_open_orders = mock.Mock(
            return_value=[cancelled_order, closed_order, active_order]
        )
        stop_automation_op_class, = automation_management.create_stop_automation_operators(exchange_manager)

        with mock.patch.object(
            exchange_manager.trader,
            "cancel_order",
            mock.AsyncMock(return_value=True),
        ) as cancel_order_mock:
            operator = stop_automation_op_class(cancel_orders=True)
            await operator.pre_compute()
            cancel_order_mock.assert_awaited_once_with(active_order, wait_for_cancelling=True)


class TestUpdateAutomationConfigurationOperator:
    @pytest.mark.asyncio
    async def test_call_as_dsl(self, interpreter_without_stop_automation):
        assert "update_automation_configuration" in interpreter_without_stop_automation.operators_by_name

        result = await interpreter_without_stop_automation.interprete(
            f"update_automation_configuration({_SAMPLE_CONFIGURATION_UPDATE_DSL!r})"
        )
        _assert_update_automation_configuration_result(result, _SAMPLE_CONFIGURATION_UPDATE_DSL)

    def test_compute(self):
        operator = automation_management.UpdateAutomationConfigurationOperator(
            _SAMPLE_CONFIGURATION_UPDATE_DSL,
        )
        result = operator.compute()
        _assert_update_automation_configuration_result(result, _SAMPLE_CONFIGURATION_UPDATE_DSL)

    @pytest.mark.asyncio
    async def test_invalid_parameters(self, interpreter_without_stop_automation):
        with pytest.raises(
            octobot_commons.errors.InvalidParametersError,
            match="requires at least 1",
        ):
            await interpreter_without_stop_automation.interprete("update_automation_configuration()")
        with pytest.raises(
            octobot_commons.errors.InvalidParametersError,
            match="supports up to 1",
        ):
            await interpreter_without_stop_automation.interprete(
                f"update_automation_configuration({_SAMPLE_CONFIGURATION_UPDATE_DSL!r}, 1)"
            )

    def test_docs(self):
        docs = automation_management.UpdateAutomationConfigurationOperator.get_docs()
        assert docs.name == "update_automation_configuration"
        assert docs.example == 'update_automation_configuration("your_dsl_call(...)")'
