import pytest

import octobot_flow.errors
import octobot_flow.parsers.actions_dag_parser as actions_dag_parser


class TestResolveParamDependencies:
    """`_resolve_param_dependencies`: top-level dataclass fields."""

    def test_alias_resolves_to_order_amount(self):
        params = actions_dag_parser.ActionsDAGParserParams.from_dict({
            "ORDER_AMOUNT": 1.5,
            "BLOCKCHAIN_FROM_AMOUNT": f"{actions_dag_parser.PARAM_DEPENDENCY_PREFIX}ORDER_AMOUNT",
        })
        assert params.BLOCKCHAIN_FROM_AMOUNT == 1.5
        assert params.ORDER_AMOUNT == 1.5

    def test_two_hop_chain(self):
        params = actions_dag_parser.ActionsDAGParserParams.from_dict({
            "ORDER_AMOUNT": 2.0,
            "BLOCKCHAIN_FROM_AMOUNT": f"{actions_dag_parser.PARAM_DEPENDENCY_PREFIX}ORDER_AMOUNT",
            "BLOCKCHAIN_TO_AMOUNT": f"{actions_dag_parser.PARAM_DEPENDENCY_PREFIX}BLOCKCHAIN_FROM_AMOUNT",
        })
        assert params.BLOCKCHAIN_TO_AMOUNT == 2.0
        assert params.BLOCKCHAIN_FROM_AMOUNT == 2.0

    def test_target_name_is_case_insensitive(self):
        prefix = actions_dag_parser.PARAM_DEPENDENCY_PREFIX
        params = actions_dag_parser.ActionsDAGParserParams.from_dict({
            "ORDER_AMOUNT": 4.0,
            "BLOCKCHAIN_FROM_AMOUNT": f"{prefix}order_amount",
            "BLOCKCHAIN_TO_AMOUNT": f"{prefix}Blockchain_From_Amount",
        })
        assert params.BLOCKCHAIN_FROM_AMOUNT == 4.0
        assert params.BLOCKCHAIN_TO_AMOUNT == 4.0


class TestResolveParamDependenciesInMapping:
    """`_resolve_param_dependencies_in_mapping`: dict-valued fields (nested dicts)."""

    def test_resolves_inside_dict_field(self):
        prefix = actions_dag_parser.PARAM_DEPENDENCY_PREFIX
        params = actions_dag_parser.ActionsDAGParserParams.from_dict({
            "BLOCKCHAIN_BALANCE_ADDRESS": "0xabc",
            "ORDER_EXTRA_PARAMS": {
                "address_to": f"{prefix}BLOCKCHAIN_BALANCE_ADDRESS",
            },
        })
        assert params.ORDER_EXTRA_PARAMS == {"address_to": "0xabc"}

    def test_resolves_inside_dict_field_case_insensitive_target(self):
        prefix = actions_dag_parser.PARAM_DEPENDENCY_PREFIX
        params = actions_dag_parser.ActionsDAGParserParams.from_dict({
            "BLOCKCHAIN_BALANCE_ADDRESS": "0xdef",
            "ORDER_EXTRA_PARAMS": {
                "address_to": f"{prefix}blockchain_balance_address",
            },
        })
        assert params.ORDER_EXTRA_PARAMS == {"address_to": "0xdef"}

    def test_resolves_nested_dict_values(self):
        prefix = actions_dag_parser.PARAM_DEPENDENCY_PREFIX
        params = actions_dag_parser.ActionsDAGParserParams.from_dict({
            "ORDER_AMOUNT": 3.0,
            "CONTENT": {
                "nested": {
                    "amount": f"{prefix}ORDER_AMOUNT",
                },
            },
        })
        assert params.CONTENT == {"nested": {"amount": 3.0}}


class TestResolveParamDependencyStringValue:
    """`_resolve_param_dependency_string_value`: invalid or deferred resolution."""

    def test_empty_suffix_raises(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            actions_dag_parser.ActionsDAGParserParams.from_dict({
                "BLOCKCHAIN_FROM_AMOUNT": actions_dag_parser.PARAM_DEPENDENCY_PREFIX,
            })

    def test_malformed_extra_segments_raises(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            actions_dag_parser.ActionsDAGParserParams.from_dict({
                "BLOCKCHAIN_FROM_AMOUNT": (
                    f"{actions_dag_parser.PARAM_DEPENDENCY_PREFIX}ORDER_AMOUNT::extra"
                ),
            })

    def test_unknown_target_raises(self):
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError) as raised:
            actions_dag_parser.ActionsDAGParserParams.from_dict({
                "BLOCKCHAIN_FROM_AMOUNT": f"{actions_dag_parser.PARAM_DEPENDENCY_PREFIX}NOT_A_FIELD",
            })
        assert "NOT_A_FIELD" in str(raised.value)

    def test_two_node_cycle_raises(self):
        prefix = actions_dag_parser.PARAM_DEPENDENCY_PREFIX
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError) as raised:
            actions_dag_parser.ActionsDAGParserParams.from_dict({
                "BLOCKCHAIN_FROM_AMOUNT": f"{prefix}BLOCKCHAIN_TO_AMOUNT",
                "BLOCKCHAIN_TO_AMOUNT": f"{prefix}BLOCKCHAIN_FROM_AMOUNT",
            })
        assert "cycle" in str(raised.value).lower() or "unresolved" in str(raised.value).lower()
