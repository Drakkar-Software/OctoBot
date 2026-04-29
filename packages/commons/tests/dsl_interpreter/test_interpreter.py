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
import dataclasses
import typing
import pytest
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import ast


@dataclasses.dataclass
class ChannelDependency(dsl_interpreter.InterpreterDependency):
    channel_name: str


class SumPlusXOperatorWithoutInit(dsl_interpreter.NaryOperator):
    def __init__(self, *parameters: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(*parameters, **kwargs)
        self.x_value = 42
    
    @staticmethod
    def get_name() -> str:
        return "plus_42"

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        return sum(computed_parameters) + self.x_value


class TimeFrameToSecondsOperator(dsl_interpreter.CallOperator):
    def __init__(self, operand: dsl_interpreter.OperatorParameterType, **kwargs: typing.Any):
        super().__init__(operand, **kwargs)

    @staticmethod
    def get_name() -> str:
        return "time_frame_to_seconds"

    def get_dependencies(self) -> typing.List[dsl_interpreter.InterpreterDependency]:
        dependencies = super().get_dependencies()
        dependencies.append(ChannelDependency("time_channel"))
        return dependencies

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        computed_parameters = self.get_computed_parameters()
        return commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(computed_parameters[0])] * commons_constants.MINUTE_TO_SECONDS


class AddOperator(dsl_interpreter.BinaryOperator):
    @staticmethod
    def get_name() -> str:
        return ast.Add.__name__

    def compute(self) -> dsl_interpreter.ComputedOperatorParameterType:
        left, right = self.get_computed_left_and_right_parameters()
        return left + right


@pytest.fixture
def interpreter():
    interpreter = dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
    )
    interpreter.extend([
        SumPlusXOperatorWithoutInit, TimeFrameToSecondsOperator, AddOperator
    ])
    return interpreter

@pytest.mark.asyncio
async def test_interprete(interpreter):
    assert isinstance(await interpreter.interprete("plus_42()"), int)
    assert await interpreter.interprete("time_frame_to_seconds('1m') + plus_42()") == 60 + 42


@pytest.mark.asyncio
async def test_prepare_and_compute_expression(interpreter):
    assert interpreter._operator_tree_or_constant is None
    interpreter.prepare("plus_42()")
    assert isinstance(interpreter._operator_tree_or_constant, dsl_interpreter.Operator)
    assert await interpreter.compute_expression() == 42
    assert await interpreter.compute_expression() == 42 # return the same value as the first time

    assert isinstance(interpreter._operator_tree_or_constant, SumPlusXOperatorWithoutInit)

    async def compute_new_value():
        interpreter._operator_tree_or_constant.x_value = 100
    with mock.patch.object(
        interpreter._operator_tree_or_constant, 'pre_compute', mock.AsyncMock(side_effect=compute_new_value)
    ):
        # now returns 100 because the same operator now has a new value (set during pre_compute())
        assert await interpreter.compute_expression() == 100
        assert await interpreter.compute_expression() == 100

    # 100 value has been saved
    assert await interpreter.compute_expression() == 100


@pytest.mark.asyncio
async def test_get_dependencies(interpreter):
    interpreter.prepare("plus_42()")
    assert interpreter.get_dependencies() == []

    interpreter.prepare("time_frame_to_seconds('1m') + plus_42()")
    assert interpreter.get_dependencies() == [
        ChannelDependency("time_channel")
    ]

    interpreter.prepare("time_frame_to_seconds('1m') + time_frame_to_seconds('1m')")
    # don't return the same dependency twice
    assert interpreter.get_dependencies() == [
        ChannelDependency("time_channel")
    ]

    # more than one dependency
    with mock.patch.object(SumPlusXOperatorWithoutInit, 'get_dependencies', mock.Mock(return_value=[ChannelDependency("plop_channel")])):
        interpreter.prepare("time_frame_to_seconds('1m') + (2 + plus_42())")
        assert interpreter.get_dependencies() == [
            ChannelDependency("time_channel"),
            ChannelDependency("plop_channel")
        ]
