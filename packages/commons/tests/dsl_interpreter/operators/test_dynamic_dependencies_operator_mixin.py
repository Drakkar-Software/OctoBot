#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.dsl_interpreter.operators.dynamic_dependencies_operator_mixin as dynamic_dependencies_operator_mixin


class _DynamicDependenciesOperator(dynamic_dependencies_operator_mixin.DynamicDependenciesOperatorMixin):
    @staticmethod
    def get_name() -> str:
        return "sample_operator"


class TestDynamicDependency:
    def test_json_round_trip(self):
        dependency = dynamic_dependencies_operator_mixin.DynamicDependency(
            operator_name="rsi_momentum_evaluator",
            result={"eval_note": -1, "evaluator_name": "RSIMomentumEvaluator"},
        )
        restored_dependency = dynamic_dependencies_operator_mixin.DynamicDependency.from_dict(
            dependency.to_dict(include_default_values=False)
        )
        assert restored_dependency.operator_name == dependency.operator_name
        assert restored_dependency.result == dependency.result

    def test_parse_entry_from_dict(self):
        dependency = dynamic_dependencies_operator_mixin.DynamicDependency.parse_entry({
            "operator_name": "dma_evaluator",
            "result": {"eval_note": 1},
        })
        assert dependency.operator_name == "dma_evaluator"
        assert dependency.result == {"eval_note": 1}

    def test_parse_entry_raises_on_invalid_entry(self):
        with pytest.raises(ValueError):
            dynamic_dependencies_operator_mixin.DynamicDependency.parse_entry("invalid")


class TestDynamicDependenciesOperatorMixin:
    def test_get_dynamic_dependencies_parameters(self):
        parameters = _DynamicDependenciesOperator.get_dynamic_dependencies_parameters()
        assert len(parameters) == 1
        assert parameters[0].name == "_dynamic_dependencies"
        assert parameters[0].type is list

    def test_dsl_statement_uses_dynamic_dependencies_true(self):
        unresolved_placeholder = commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER
        assert dynamic_dependencies_operator_mixin.DynamicDependenciesOperatorMixin.dsl_statement_uses_dynamic_dependencies(
            f"strategy_evaluator(symbol='BTC/USDC', _dynamic_dependencies={unresolved_placeholder})"
        ) is True

    def test_dsl_statement_uses_dynamic_dependencies_false(self):
        assert dynamic_dependencies_operator_mixin.DynamicDependenciesOperatorMixin.dsl_statement_uses_dynamic_dependencies(
            "strategy_evaluator(symbol='BTC/USDC')"
        ) is False

    def test_get_dynamic_dependencies_from_list(self):
        operator = _DynamicDependenciesOperator()
        dependencies = operator.get_dynamic_dependencies({
            "_dynamic_dependencies": [
                {
                    "operator_name": "double_moving_average_trend_evaluator",
                    "result": {
                        "eval_note": 1,
                        "symbol": "BTC/USDC",
                        "time_frame": "2h",
                    },
                },
                {
                    "operator_name": "r_s_i_momentum_evaluator",
                    "result": {
                        "eval_note": -1,
                        "symbol": "BTC/USDC",
                        "time_frame": "2h",
                    },
                },
            ],
        })
        assert len(dependencies) == 2
        assert dependencies[0].operator_name == "double_moving_average_trend_evaluator"
        assert dependencies[1].operator_name == "r_s_i_momentum_evaluator"

    def test_get_dynamic_dependencies_from_scalar_entry(self):
        operator = _DynamicDependenciesOperator()
        dependencies = operator.get_dynamic_dependencies({
            "_dynamic_dependencies": {
                "operator_name": "simple_strategy_evaluator",
                "result": {
                    "eval_note": 0,
                    "symbol": "BTC/USDC",
                    "time_frame": "2h",
                },
            },
        })
        assert len(dependencies) == 1
        assert dependencies[0].operator_name == "simple_strategy_evaluator"
