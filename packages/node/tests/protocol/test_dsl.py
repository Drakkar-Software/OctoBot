#  Drakkar-Software OctoBot-Node
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

import octobot_commons.enums as commons_enums
import octobot_commons.dsl_interpreter.operator_docs as dsl_interpreter_operator_docs
import octobot_commons.dsl_interpreter.operator_parameter as dsl_interpreter_operator_parameter
import octobot_node.protocol.dsl as dsl_protocol
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants


def _sample_parameter(
    name: str = "period",
    parameter_type: str = commons_enums.DslValueType.NUMBER.value,
    default=dsl_interpreter_operator_parameter.UNSET_VALUE,
    **parameter_kwargs,
) -> dsl_interpreter_operator_parameter.OperatorParameter:
    return dsl_interpreter_operator_parameter.OperatorParameter(
        name=name,
        description="lookback",
        required=True,
        type=parameter_type,
        default=default,
        **parameter_kwargs,
    )


def _sample_docs(**overrides) -> dsl_interpreter_operator_docs.OperatorDocs:
    data = {
        "name": "rsi",
        "description": "Relative Strength Index",
        "type": "ta",
        "example": "rsi(data, 14)",
        "parameters": [
            _sample_parameter(
                name="data",
                parameter_type=commons_enums.DslValueType.SERIES.value,
            )
        ],
        "label": "RSI",
        "category": commons_enums.DslKeywordCategory.SOURCE.value,
        "return_values": [
            dsl_interpreter_operator_parameter.OperatorParameter(
                name="result",
                description="RSI series",
                required=True,
                type=commons_enums.DslValueType.SERIES.value,
            )
        ],
    }
    data.update(overrides)
    return dsl_interpreter_operator_docs.OperatorDocs(**data)


class TestListDslOperatorDocs:
    def test_returns_non_empty_operator_docs(self):
        operator_docs_list = dsl_protocol.list_dsl_operator_docs()
        assert len(operator_docs_list) > 0
        assert all(
            isinstance(operator_docs, dsl_interpreter_operator_docs.OperatorDocs)
            for operator_docs in operator_docs_list
        )

    def test_uses_flow_operator_assembly(self):
        operator_names = {
            operator_docs.name
            for operator_docs in dsl_protocol.list_dsl_operator_docs()
        }
        assert "fetch_order" in operator_names
        assert "copy_exchange_account" in operator_names
        assert "run_octobot_process" in operator_names
        assert "blockchain_wallet_balance" in operator_names
        assert "set_leverage" not in operator_names
        assert len(operator_names) > 69


class TestOperatorParameterToDslParameter:
    def test_maps_authored_type_and_default(self):
        operator_parameter = _sample_parameter(default=14)
        dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            operator_parameter
        )
        assert dsl_parameter.name == "period"
        assert dsl_parameter.label == "period"
        assert dsl_parameter.value_type is protocol_models.DslValueType.NUMBER
        assert dsl_parameter.required is True
        assert dsl_parameter.default_value is not None
        assert dsl_parameter.default_value.actual_instance == 14

    def test_skips_none_default(self):
        operator_parameter = _sample_parameter(default=None)
        dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            operator_parameter
        )
        assert dsl_parameter.default_value is None

    def test_skips_structured_default(self):
        operator_parameter = _sample_parameter(
            default=[{"crypto-currency": "Bitcoin"}],
            parameter_type=commons_enums.DslValueType.ANY.value,
        )
        dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            operator_parameter
        )
        assert dsl_parameter.default_value is None

    def test_raises_when_type_missing(self):
        operator_parameter = dsl_interpreter_operator_parameter.OperatorParameter(
            name="data",
            description="series",
            required=True,
            type="",
        )
        with pytest.raises(ValueError, match="missing type"):
            dsl_protocol.operator_parameter_to_dsl_parameter(operator_parameter)

    def test_raises_when_type_unknown(self):
        operator_parameter = _sample_parameter(parameter_type="not_a_type")
        with pytest.raises(ValueError, match="unknown type"):
            dsl_protocol.operator_parameter_to_dsl_parameter(operator_parameter)

    def test_skips_unset_default(self):
        operator_parameter = _sample_parameter()
        dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            operator_parameter
        )
        assert dsl_parameter.default_value is None

    def test_maps_bool_and_str_defaults(self):
        bool_parameter = _sample_parameter(
            name="enabled",
            parameter_type=commons_enums.DslValueType.BOOLEAN.value,
            default=True,
        )
        bool_dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            bool_parameter
        )
        assert bool_dsl_parameter.default_value is not None
        assert bool_dsl_parameter.default_value.actual_instance is True

        text_parameter = _sample_parameter(
            name="symbol",
            parameter_type=commons_enums.DslValueType.TEXT.value,
            default="BTC/USDT",
        )
        text_dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            text_parameter
        )
        assert text_dsl_parameter.default_value is not None
        assert text_dsl_parameter.default_value.actual_instance == "BTC/USDT"

    def test_maps_options(self):
        operator_parameter = _sample_parameter(
            name="time_frame",
            parameter_type=commons_enums.DslValueType.TIME_FRAME.value,
            options=[
                dsl_interpreter_operator_parameter.OperatorParameterOption(
                    value="1h",
                    label="1 hour",
                ),
                dsl_interpreter_operator_parameter.OperatorParameterOption(
                    value="4h",
                    label="4 hours",
                ),
            ],
        )
        dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            operator_parameter
        )
        assert dsl_parameter.options is not None
        assert len(dsl_parameter.options) == 2
        assert dsl_parameter.options[0].value == "1h"
        assert dsl_parameter.options[0].label == "1 hour"
        assert dsl_parameter.options[1].value == "4h"
        assert dsl_parameter.options[1].label == "4 hours"

    def test_maps_numeric_constraints(self):
        operator_parameter = _sample_parameter(
            minimum=1.0,
            maximum=100.0,
            step=0.5,
        )
        dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            operator_parameter
        )
        assert dsl_parameter.minimum == 1.0
        assert dsl_parameter.maximum == 100.0
        assert dsl_parameter.step == 0.5

    def test_maps_multiple_and_primary(self):
        operator_parameter = _sample_parameter(multiple=True, primary=True)
        dsl_parameter = dsl_protocol.operator_parameter_to_dsl_parameter(
            operator_parameter
        )
        assert dsl_parameter.multiple is True
        assert dsl_parameter.primary is True


class TestOperatorDocsToDslKeyword:
    def test_maps_inputs_and_outputs(self):
        keyword = dsl_protocol.operator_docs_to_dsl_keyword(_sample_docs())
        assert keyword.name == "rsi"
        assert keyword.category is protocol_models.DslKeywordCategory.SOURCE
        assert keyword.label == "RSI"
        assert len(keyword.inputs) == 1
        assert keyword.inputs[0].value_type is protocol_models.DslValueType.SERIES
        assert len(keyword.outputs) == 1
        assert keyword.outputs[0].value_type is protocol_models.DslValueType.SERIES

    def test_raises_when_category_missing(self):
        with pytest.raises(ValueError, match="CATEGORY"):
            dsl_protocol.operator_docs_to_dsl_keyword(_sample_docs(category=""))

    def test_raises_when_return_values_missing(self):
        with pytest.raises(ValueError, match="return_values"):
            dsl_protocol.operator_docs_to_dsl_keyword(_sample_docs(return_values=[]))

    def test_raises_when_category_unknown(self):
        with pytest.raises(ValueError, match="unknown category"):
            dsl_protocol.operator_docs_to_dsl_keyword(
                _sample_docs(category="not_a_category")
            )

    def test_falls_back_label_to_name(self):
        keyword = dsl_protocol.operator_docs_to_dsl_keyword(_sample_docs(label=""))
        assert keyword.label == "rsi"
        assert keyword.label == keyword.name

    def test_raises_when_parameter_type_invalid(self):
        with pytest.raises(ValueError, match="unknown type"):
            dsl_protocol.operator_docs_to_dsl_keyword(
                _sample_docs(
                    parameters=[
                        _sample_parameter(
                            name="data",
                            parameter_type="not_a_type",
                        )
                    ]
                )
            )


class TestGetDslKeywordsState:
    def test_returns_full_catalog(self):
        dsl_keywords_state = dsl_protocol.get_dsl_keywords_state()
        assert (
            dsl_keywords_state.version == sync_constants.DSL_KEYWORDS_STATE_VERSION
        )
        assert dsl_keywords_state.version == "1.2.2"
        assert len(dsl_keywords_state.keywords) == len(
            dsl_protocol.list_dsl_operator_docs()
        )
        assert len(dsl_keywords_state.keywords) > 69
        assert all(
            isinstance(keyword, protocol_models.DslKeyword)
            for keyword in dsl_keywords_state.keywords
        )
