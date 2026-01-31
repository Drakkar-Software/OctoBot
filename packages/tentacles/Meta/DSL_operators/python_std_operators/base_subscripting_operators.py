# pylint: disable=missing-function-docstring
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
import ast
import numpy as np
import typing

import octobot_commons.errors
import octobot_commons.dsl_interpreter.operators.subscripting_operator as dsl_interpreter_subscripting_operator
import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator


class SubscriptOperator(dsl_interpreter_subscripting_operator.SubscriptingOperator):
    """
    Base class for subscripting operators: array[index]
    Subscripting operators have three operands: the array/list, the index or slice and the context.
    """
    NAME = "[...]"
    DESCRIPTION = "Subscripting operator. Accesses an element from a list or array using an index."
    EXAMPLE = "my_list[0]"

    def __init__(
        self,
        array_or_list: dsl_interpreter_operator.OperatorParameterType,
        index_or_slice: dsl_interpreter_operator.OperatorParameterType,
        context: dsl_interpreter_operator.OperatorParameterType,
        **kwargs: typing.Any
    ):
        """
        Initialize the subscripting operator with its array, index and context.
        """
        super().__init__(array_or_list, index_or_slice, context, **kwargs)

    def get_computed_array_or_list_and_index_or_slice_and_context_parameters(
        self,
    ) -> typing.Tuple[
        dsl_interpreter_operator.ComputedOperatorParameterType,
        dsl_interpreter_operator.ComputedOperatorParameterType,
        dsl_interpreter_operator.ComputedOperatorParameterType,
    ]:
        """
        Get the computed array/list, index/slice and context of the subscripting operator.
        """
        computed_parameters = self.get_computed_parameters()
        if len(computed_parameters) != 3:
            raise octobot_commons.errors.InvalidParametersError(f"Unsupported {self.__class__.__name__}: expected three parameters, got {len(computed_parameters)}")
        if not isinstance(computed_parameters, (list, tuple, np.ndarray)):
            raise octobot_commons.errors.InvalidParametersError(f"Unsupported {self.__class__.__name__} computed parameters 1 type: {type(computed_parameters).__name__}")
        return computed_parameters[0], computed_parameters[1], computed_parameters[2]

    @staticmethod
    def get_name() -> str:
        return ast.Subscript.__name__

    def compute(self) -> dsl_interpreter_operator.ComputedOperatorParameterType:
        # Compute the test condition
        array_or_list, index, context = self.get_computed_array_or_list_and_index_or_slice_and_context_parameters()
        if isinstance(context, ast.Load):
            return array_or_list[index]
        raise octobot_commons.errors.InvalidParametersError(f"Unsupported {self.__class__.__name__} context type: {type(context).__name__}")


class SliceOperator(dsl_interpreter_subscripting_operator.SubscriptingOperator):
    """
    Operator for creating slice objects: slice(lower, upper, step)
    Used for array slicing like array[start:stop:step]
    """
    NAME = "[start:stop:step]"
    DESCRIPTION = "Slice operator. Creates a slice object for array/list slicing with optional start, stop, and step parameters."
    EXAMPLE = "my_list[1:5:2]"

    @staticmethod
    def get_name() -> str:
        return ast.Slice.__name__

    def get_computed_lower_and_upper_and_step_parameters(
        self,
    ) -> typing.Tuple[
        dsl_interpreter_operator.ComputedOperatorParameterType,
        dsl_interpreter_operator.ComputedOperatorParameterType,
        dsl_interpreter_operator.ComputedOperatorParameterType,
    ]:
        """
        Get the computed lower, upper and step of the slice operator.
        """
        computed_parameters = self.get_computed_parameters()
        if len(computed_parameters) > 3:
            raise octobot_commons.errors.InvalidParametersError(f"Unsupported {self.__class__.__name__}: expected at most three parameters, got {len(computed_parameters)}")
        lower = int(computed_parameters[0]) if len(computed_parameters) > 0 and computed_parameters[0] is not None else None
        upper = int(computed_parameters[1]) if len(computed_parameters) > 1 and computed_parameters[1] is not None else None
        step = int(computed_parameters[2]) if len(computed_parameters) > 2 and computed_parameters[2] is not None else None
        return lower, upper, step

    def compute(self) -> slice:
        """
        Compute and return a Python slice object.
        """
        maybe_lower, maybe_upper, maybe_step = self.get_computed_lower_and_upper_and_step_parameters()
        if maybe_lower is not None:
            if maybe_upper is not None:
                if maybe_step is not None:
                    return slice(maybe_lower, maybe_upper, maybe_step)
                return slice(maybe_lower, maybe_upper, None)
            return slice(maybe_lower, None, None)
        if maybe_upper is not None:
            return slice(None, maybe_upper, None)
        return slice(None, None, None)
