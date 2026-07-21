#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.
"""
Convert DSL operator documentation to protocol DslKeywordsState.

inputs are derived from get_parameters() / OperatorDocs.parameters.
outputs are derived from get_return_values() / OperatorDocs.return_values.
"""
import typing

import octobot_commons.dsl_interpreter.operator_docs as dsl_interpreter_operator_docs
import octobot_commons.dsl_interpreter.operator_parameter as dsl_interpreter_operator_parameter
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants


_CATALOG_EXECUTOR_ID = "dsl-keywords-catalog"


def list_dsl_operator_docs() -> list[dsl_interpreter_operator_docs.OperatorDocs]:
    """
    Collect operator documentation for keywords exposed by the node.

    Uses the same operator set as flow DSLExecutor.get_flow_operator_classes.
    """
    # Lazy: flow → tentacles; keep module import safe for build_openapi packaging.
    import octobot_flow.logic.configuration.profile_data_factory as profile_data_factory
    import octobot_flow.logic.dsl.dsl_executor as dsl_executor_module

    catalog_profile_data = profile_data_factory.create_profile_data(
        None,
        _CATALOG_EXECUTOR_ID,
        set(),
    )
    catalog_executor = dsl_executor_module.DSLExecutor(
        catalog_profile_data,
        None,
        None,
        executor_id=_CATALOG_EXECUTOR_ID,
    )
    operator_classes = catalog_executor.get_flow_operator_classes(
        _CATALOG_EXECUTOR_ID,
    )
    return [operator_class.get_docs() for operator_class in operator_classes]


def operator_parameter_to_dsl_parameter(
    parameter: dsl_interpreter_operator_parameter.OperatorParameter,
) -> protocol_models.DslParameter:
    """
    Map an OperatorParameter to a protocol DslParameter.

    Requires an authored DslValueType string on parameter.type.
    """
    if not parameter.type:
        raise ValueError(
            f"OperatorParameter {parameter.name!r} is missing type; "
            "author a DslValueType-compatible type on the operator parameter"
        )
    try:
        value_type = protocol_models.DslValueType(parameter.type)
    except ValueError as error:
        raise ValueError(
            f"OperatorParameter {parameter.name!r} has unknown type "
            f"{parameter.type!r}"
        ) from error

    dsl_parameter_kwargs: dict[str, typing.Any] = {
        "name": parameter.name,
        "label": parameter.name,
        "value_type": value_type,
        "description": parameter.description,
        "required": parameter.required,
    }
    if (
        parameter.default is not dsl_interpreter_operator_parameter.UNSET_VALUE
        and parameter.default is not None
        and isinstance(parameter.default, (bool, int, float, str))
    ):
        # Protocol DslParameterDefaultValue only accepts bool | float | str (int via float).
        # Skip None and structured defaults (list/dict) that the schema cannot represent.
        dsl_parameter_kwargs["default_value"] = (
            protocol_models.DslParameterDefaultValue(parameter.default)
        )
    if parameter.options is not None:
        dsl_parameter_kwargs["options"] = [
            protocol_models.DslParameterOption(
                value=option.value,
                label=option.label,
            )
            for option in parameter.options
        ]
    if parameter.minimum is not None:
        dsl_parameter_kwargs["minimum"] = parameter.minimum
    if parameter.maximum is not None:
        dsl_parameter_kwargs["maximum"] = parameter.maximum
    if parameter.step is not None:
        dsl_parameter_kwargs["step"] = parameter.step
    if parameter.multiple is not None:
        dsl_parameter_kwargs["multiple"] = parameter.multiple
    if parameter.primary is not None:
        dsl_parameter_kwargs["primary"] = parameter.primary
    return protocol_models.DslParameter(**dsl_parameter_kwargs)


def operator_docs_to_dsl_keyword(
    operator_docs: dsl_interpreter_operator_docs.OperatorDocs,
) -> protocol_models.DslKeyword:
    """
    Convert operator documentation to a protocol DslKeyword.

    Raises ValueError when required catalog metadata is missing.
    """
    if not operator_docs.category:
        raise ValueError(
            f"Operator {operator_docs.name!r} is missing CATEGORY; "
            "author a DslKeywordCategory-compatible CATEGORY on the operator"
        )
    try:
        category = protocol_models.DslKeywordCategory(operator_docs.category)
    except ValueError as error:
        raise ValueError(
            f"Operator {operator_docs.name!r} has unknown category "
            f"{operator_docs.category!r}"
        ) from error
    if not operator_docs.return_values:
        raise ValueError(
            f"Operator {operator_docs.name!r} is missing return_values; "
            "author get_return_values() on the operator"
        )

    return protocol_models.DslKeyword(
        name=operator_docs.name,
        category=category,
        label=operator_docs.label or operator_docs.name,
        description=operator_docs.description,
        inputs=[
            operator_parameter_to_dsl_parameter(parameter)
            for parameter in operator_docs.parameters
        ],
        outputs=[
            operator_parameter_to_dsl_parameter(return_value)
            for return_value in operator_docs.return_values
        ],
    )


def get_dsl_keywords_state() -> protocol_models.DslKeywordsState:
    """
    Return the DSL keywords state for this node.
    """
    keywords = [
        operator_docs_to_dsl_keyword(operator_docs)
        for operator_docs in list_dsl_operator_docs()
    ]
    return protocol_models.DslKeywordsState(
        version=sync_constants.DSL_KEYWORDS_STATE_VERSION,
        keywords=keywords,
    )
