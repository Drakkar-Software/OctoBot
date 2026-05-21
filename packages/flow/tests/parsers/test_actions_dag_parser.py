import json

import pytest

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.parsers.actions_dag_parser as actions_dag_parser
import octobot_trading.constants as trading_constants


def dsl_if_error_decode_on_error(dsl_script: str) -> str:
    remainder = dsl_script[dsl_script.index("on_error=") + len("on_error=") :].lstrip()
    recovery_source, _end = json.JSONDecoder().raw_decode(remainder)
    return recovery_source


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


class TestGetBlockchainAndSpecificConfigs:
    """`get_blockchain_and_specific_configs`: unknown blockchain network."""

    def test_invalid_blockchain_raises_invalid_automation_action_error(self):
        params = actions_dag_parser.ActionsDAGParserParams.from_dict({})
        invalid_blockchain = "invalid_blockchain_xyz"
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError) as raised:
            params.get_blockchain_and_specific_configs(invalid_blockchain)
        assert str(raised.value) == f"Invalid blockchain: {invalid_blockchain}"
        assert isinstance(raised.value.__cause__, KeyError)


class TestParseWalletCleanupIfError:
    """`parse` / `_parse_generic_actions`: if_error wrapper after open wallet init."""

    _wallet_address = "0x1234567890123456789012345678901234567890"
    _wallet_private_key = (
        "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    )

    def _simulated_blockchain_wallet_init_then_wait_params(self) -> dict:
        return {
            "ACTIONS": [
                actions_dag_parser.ActionType.BLOCKCHAIN_WALLET_INIT.value,
                actions_dag_parser.ActionType.WAIT.value,
            ],
            "BLOCKCHAIN_FROM": trading_constants.SIMULATED_BLOCKCHAIN_NETWORK,
            "BLOCKCHAIN_FROM_ASSET": "ETH",
            "BLOCKCHAIN_FROM_AMOUNT": 10.0,
            "BLOCKCHAIN_FROM_ADDRESS": self._wallet_address,
            "BLOCKCHAIN_FROM_PRIVATE_KEY": self._wallet_private_key,
            "MIN_DELAY": 1.0,
        }

    def _extract_wait_action(
        self,
        actions_dag: octobot_flow.entities.ActionsDAG,
    ) -> octobot_flow.entities.DSLScriptActionDetails:
        wait_action = next(action for action in actions_dag.actions if action.id == "action_wait_2")
        assert isinstance(wait_action, octobot_flow.entities.DSLScriptActionDetails)
        return wait_action

    def _wait_action_after_parse(self, params: dict) -> octobot_flow.entities.DSLScriptActionDetails:
        return self._extract_wait_action(actions_dag_parser.ActionsDAGParser(params).parse())

    def test_wraps_following_wait_when_close_wallet_on_exit_false(self):
        params = {
            **self._simulated_blockchain_wallet_init_then_wait_params(),
            "BLOCKCHAIN_INIT_CLOSE_WALLET_ON_EXIT": False,
        }
        parser = actions_dag_parser.ActionsDAGParser(params)
        wait_action = self._extract_wait_action(parser.parse())
        assert wait_action.dsl_script.startswith("if_error(")
        assert "on_error=" in wait_action.dsl_script
        expected_recovery = parser._build_blockchain_wallet_init_dsl(
            force_close_wallet_on_exit=True,
        )
        assert dsl_if_error_decode_on_error(wait_action.dsl_script) == expected_recovery

    def test_wraps_following_wait_when_close_wallet_on_exit_omitted(self):
        params = self._simulated_blockchain_wallet_init_then_wait_params()
        parser = actions_dag_parser.ActionsDAGParser(params)
        wait_action = self._extract_wait_action(parser.parse())
        assert wait_action.dsl_script.startswith("if_error(")
        expected_recovery = parser._build_blockchain_wallet_init_dsl(
            force_close_wallet_on_exit=True,
        )
        assert dsl_if_error_decode_on_error(wait_action.dsl_script) == expected_recovery

    def test_does_not_wrap_when_close_wallet_on_exit_true(self):
        params = {
            **self._simulated_blockchain_wallet_init_then_wait_params(),
            "BLOCKCHAIN_INIT_CLOSE_WALLET_ON_EXIT": True,
        }
        wait_action = self._wait_action_after_parse(params)
        assert wait_action.dsl_script.startswith("wait(")
        assert "if_error(" not in wait_action.dsl_script
