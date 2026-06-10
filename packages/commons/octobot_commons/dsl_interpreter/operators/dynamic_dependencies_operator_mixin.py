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
import dataclasses
import typing

import octobot_commons.dataclasses
import octobot_commons.dsl_interpreter.operator_parameter as operator_parameter


@dataclasses.dataclass
class DynamicDependency(octobot_commons.dataclasses.MinimizableDataclass):
    operator_name: str
    result: dict

    @classmethod
    def parse_entry(cls, entry: typing.Any) -> "DynamicDependency":
        """
        Parse a dict or DynamicDependency entry into a DynamicDependency instance.
        """
        if isinstance(entry, DynamicDependency):
            return entry
        if not isinstance(entry, dict):
            raise ValueError(
                f"Dynamic dependency entry must be a dict or DynamicDependency, got {type(entry).__name__}"
            )
        try:
            return cls.from_dict(entry)
        except TypeError as error:
            raise ValueError(
                f"Cannot parse dynamic dependency entry: {entry}"
            ) from error


class DynamicDependenciesOperatorMixin:
    """
    Mixin for operators that accept upstream operator results injected via the flow DAG.
    """
    DYNAMIC_DEPENDENCIES_KEY = "_dynamic_dependencies"

    @classmethod
    def get_dynamic_dependencies_parameters(cls) -> list[operator_parameter.OperatorParameter]:
        """
        Return the optional _dynamic_dependencies operator parameter definition.
        """
        return [
            operator_parameter.OperatorParameter(
                name=cls.DYNAMIC_DEPENDENCIES_KEY,
                description="Injected upstream operator results (list of DynamicDependency JSON objects)",
                required=False,
                type=list,
                default=None,
            ),
        ]

    @staticmethod
    def dsl_statement_uses_dynamic_dependencies(dsl_script: str) -> bool:
        """
        Return True when the DSL script passes the _dynamic_dependencies keyword.
        """
        try:
            parsed_expression = ast.parse(dsl_script, mode="eval")
        except SyntaxError:
            return False
        if not isinstance(parsed_expression.body, ast.Call):
            return False
        for keyword in parsed_expression.body.keywords:
            if keyword.arg == DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY:
                return True
        return False

    def get_dynamic_dependencies(
        self,
        param_by_name: dict[str, typing.Any],
    ) -> list[DynamicDependency]:
        """
        Parse injected upstream operator results from resolved operator parameters.
        """
        dynamic_dependencies_value = param_by_name.get(self.DYNAMIC_DEPENDENCIES_KEY)
        if dynamic_dependencies_value is None:
            return []
        if isinstance(dynamic_dependencies_value, list):
            dependency_entries = dynamic_dependencies_value
        else:
            dependency_entries = [dynamic_dependencies_value]
        return [
            DynamicDependency.parse_entry(dependency_entry)
            for dependency_entry in dependency_entries
        ]
