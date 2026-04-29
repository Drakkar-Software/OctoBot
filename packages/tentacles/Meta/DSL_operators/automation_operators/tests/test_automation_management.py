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
import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.errors
import octobot_flow.entities

import tentacles.Meta.DSL_operators.automation_operators.automation_management as automation_management


@pytest.fixture
def interpreter():
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
    )


def _assert_stop_automation_result(result):
    assert isinstance(result, dict)
    assert octobot_flow.entities.PostIterationActionsDetails.__name__ in result
    details = octobot_flow.entities.PostIterationActionsDetails.from_dict(
        result[octobot_flow.entities.PostIterationActionsDetails.__name__]
    )
    assert details.stop_automation is True


@pytest.mark.asyncio
async def test_stop_automation_call_as_dsl(interpreter):
    assert "stop_automation" in interpreter.operators_by_name

    result = await interpreter.interprete("stop_automation()")
    _assert_stop_automation_result(result)


def test_stop_automation_operator_compute():
    operator = automation_management.StopAutomationOperator()
    result = operator.compute()
    _assert_stop_automation_result(result)


@pytest.mark.asyncio
async def test_stop_automation_operator_invalid_parameters(interpreter):
    with pytest.raises(
        octobot_commons.errors.InvalidParametersError,
        match="supports up to 0 parameters",
    ):
        await interpreter.interprete("stop_automation(1)")


def test_stop_automation_operator_docs():
    docs = automation_management.StopAutomationOperator.get_docs()
    assert docs.name == "stop_automation"
    assert "stop" in docs.description.lower()
    assert docs.example == "stop_automation()"
