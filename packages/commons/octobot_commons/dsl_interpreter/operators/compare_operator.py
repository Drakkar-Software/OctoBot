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

import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class CompareOperator(
    dsl_interpreter_operator.Operator
):  # pylint: disable=abstract-method
    """
    Base class for compare operators.
    Compare operators have two operands.
    """

    def __init__(
        self,
        left: dsl_interpreter_operator.OperatorParameterType,
        right: dsl_interpreter_operator.OperatorParameterType,
        **kwargs: typing.Any
    ):
        """
        Initialize the compare operator with its left and right operands.
        """
        super().__init__(left, right, **kwargs)

    def get_computed_left_and_right_parameters(
        self,
    ) -> typing.Tuple[
        dsl_interpreter_operator.ComputedOperatorParameterType,
        dsl_interpreter_operator.ComputedOperatorParameterType,
    ]:
        """
        Get the computed left and right computed operands.
        """
        computed_parameters = self.get_computed_parameters()
        return computed_parameters[0], computed_parameters[1]
