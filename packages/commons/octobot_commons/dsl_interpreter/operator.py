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
import collections
import numpy as np

import octobot_commons.errors
import octobot_commons.constants
import octobot_commons.dsl_interpreter.interpreter_dependency as dsl_interpreter_dependency
import octobot_commons.dsl_interpreter.operator_parameter as dsl_interpreter_operator_parameter
import octobot_commons.dsl_interpreter.operator_docs as dsl_interpreter_operator_docs

ComputedOperatorParameterType = typing.Union[
    str, int, float, bool, None, list, dict, np.ndarray
]
OperatorParameterType = typing.Union[
    str, int, float, bool, None, list, dict, np.ndarray, "Operator"
]


class Operator:
    """
    Operator class is used to represent an operator in the DSL.
    It can have one or more parameters which are used to compute the result of the operator.
    """

    MIN_PARAMS: typing.Optional[int] = (
        None  # min number of parameters when not defined in get_parameters()
    )
    MAX_PARAMS: typing.Optional[int] = (
        None  # max number of parameters when not defined in get_parameters()
    )
    NAME: str = (
        ""  # name of the operator as written in the DSL expression, if not provided, get_name() will be used
    )
    DESCRIPTION: str = ""  # description of the operator
    EXAMPLE: str = ""  # example of the operator in the DSL

    def __init__(self, *parameters: OperatorParameterType, **kwargs: typing.Any):
        self._validate_parameters(parameters, kwargs)
        self.parameters = parameters
        self.kwargs = kwargs

    @staticmethod
    def get_name() -> str:
        """
        Get the name of the operator, as seen in the AST parsed expression.
        """
        raise NotImplementedError("get_name is not implemented")

    @staticmethod
    def get_library() -> str:
        """
        Get the library of the operator.
        """
        return octobot_commons.constants.BASE_OPERATORS_LIBRARY

    def _validate_parameters(
        self, parameters: list[OperatorParameterType], kwargs: dict[str, OperatorParameterType]
    ) -> None:
        """
        Validate the parameters of the operator.
        """
        if self.MIN_PARAMS is not None and len(parameters) < self.MIN_PARAMS:
            raise octobot_commons.errors.InvalidParametersError(
                f"{self.get_name()} requires at least {self.MIN_PARAMS} parameter(s)"
            )
        if self.MAX_PARAMS is not None and len(parameters) > self.MAX_PARAMS:
            raise octobot_commons.errors.InvalidParametersError(
                f"{self.get_name()} supports up to {self.MAX_PARAMS} parameters"
            )
        if expected_parameters := self.get_parameters():
            min_params = len(tuple(p for p in expected_parameters if p.required))
            max_params = len(tuple(p for p in expected_parameters))
            total_params = len(parameters) + len(kwargs)
            if total_params < min_params:
                raise octobot_commons.errors.InvalidParametersError(
                    f"{self.get_name()} requires at least {min_params} "
                    f"parameter(s): {self.get_parameters_description()}"
                )
            if max_params is not None and total_params > max_params:
                raise octobot_commons.errors.InvalidParametersError(
                    f"{self.get_name()} supports up to {max_params} "
                    f"parameters: {self.get_parameters_description()}"
                )

    @classmethod
    def get_parameters_description(cls) -> str:
        """
        Get the description of the parameters of the operator.
        """
        return ", ".join(
            (f"{i+1}: {param}" for i, param in enumerate(cls.get_parameters()))
        )

    @classmethod
    def get_docs(cls) -> dsl_interpreter_operator_docs.OperatorDocs:
        """
        Get the documentation of the operator.
        """
        return dsl_interpreter_operator_docs.OperatorDocs(
            name=cls.NAME or cls.get_name(),
            description=cls.DESCRIPTION,
            type=cls.get_library(),
            example=cls.EXAMPLE,
            parameters=cls.get_parameters(),
        )

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter_operator_parameter.OperatorParameter]:
        """
        return: the description of the parameters of the operator.
        """
        return []

    async def pre_compute(self) -> None:  # rename pre_compute
        """
        Refreshes the operator data, override if necessary.
        Will always be called before compute()
        """
        for parameter in self.parameters:
            if isinstance(parameter, Operator):
                await parameter.pre_compute()

    def compute(self) -> ComputedOperatorParameterType:
        """
        Compute the result of the operator considering its computed parameters.
        """
        raise NotImplementedError("compute is not implemented")

    def get_computed_parameters(self) -> list[ComputedOperatorParameterType]:
        """
        Get the computed parameters of the operator.
        Here computed means that any nested operator has already been computed.
        """
        return [self._get_computed_parameter(parameter) for parameter in self.parameters]

    def _get_computed_parameter(self, parameter: OperatorParameterType) -> ComputedOperatorParameterType:
        if isinstance(parameter, Operator):
            return parameter.compute()
        if isinstance(parameter, dict):
            return {self._get_computed_parameter(k): self._get_computed_parameter(v) for k, v in parameter.items()}
        if isinstance(parameter, list):
            return [self._get_computed_parameter(v) for v in parameter]
        return parameter

    def get_computed_kwargs(self) -> dict[str, ComputedOperatorParameterType]:
        """
        Get the computed kwargs of the operator.
        """
        return {
            kw: value.compute() if isinstance(value, Operator) else value
            for kw, value in self.kwargs.items()
        }

    def get_computed_value_by_parameter(self) -> dict[str, ComputedOperatorParameterType]:
        """
        Get the COMPUTED value of each parameter by its name.
        """
        computed_parameters_queue = collections.deque(self.get_computed_parameters())
        computed_kwargs = self.get_computed_kwargs()
        return self._get_value_by_parameter(computed_parameters_queue, computed_kwargs) # type: ignore

    def get_input_value_by_parameter(self) -> dict[str, OperatorParameterType]:
        """
        Get the raw input (uncomputed) value of each parameter by its name.
        """
        return self._get_value_by_parameter(
            collections.deque(self.parameters), dict(self.kwargs)
        )

    def _get_value_by_parameter(
        self,
        args: collections.deque[OperatorParameterType],
        kwargs: dict[str, OperatorParameterType]
    ) -> dict[str, OperatorParameterType]:
        """
        Get the value of each parameter by its name. 
        If a value is not provided, the default value will be used if available, 
        otherwise the parameter will be skipped.
        """
        value_by_parameter = {}
        for parameter in self.get_parameters():
            # 1. non kw parameters are first
            if args:
                value_by_parameter[parameter.name] = args.popleft()
            else:
                # 2. no more non kw parameters, explore kw parameters
                if parameter.name in kwargs:
                    if parameter.name in value_by_parameter:
                        raise octobot_commons.errors.InvalidParametersError(
                            f"Parameter {parameter.name} has multiple values"
                        )
                    value_by_parameter[parameter.name] = kwargs[parameter.name]
                    kwargs.pop(parameter.name)
                else:
                    # 3. try to get the default value if set
                    if parameter.default is not dsl_interpreter_operator_parameter.UNSET_VALUE:
                        value_by_parameter[parameter.name] = parameter.default
        if kwargs:
            parameter_names = [p.name for p in self.get_parameters()] # use a list to preserve order
            if unknown_parameters := {
                k: v for k, v in kwargs.items() if k not in parameter_names
            }:
                raise octobot_commons.errors.InvalidParametersError(
                    f"Parameter(s) {', '.join(f"'{k}'" for k in unknown_parameters.keys())} "
                    f"are unknown. Supported parameters: {', '.join(parameter_names)}"
                )
            raise octobot_commons.errors.InvalidParametersError(
                f"Parameter(s) {', '.join(f"'{k}'" for k in kwargs.keys())} "
                f"have multiple values"
            )
        return value_by_parameter

    def get_dependencies(
        self,
    ) -> list[dsl_interpreter_dependency.InterpreterDependency]:
        """
        Get the dependencies of the operator.
        """
        dependencies = []
        for parameter in self.parameters:
            if isinstance(parameter, Operator):
                dependencies.extend(parameter.get_dependencies())
        return dependencies
