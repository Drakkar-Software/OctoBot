import decimal
import json
import time

import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.errors as commons_errors
import octobot_copy.constants as copy_constants
import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models
import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.logic.actions.account_copy_util as account_copy_util
import octobot_flow.logic.actions.actions_factory as actions_factory

STRATEGY_ID = "test-copy-strategy"
REFERENCE_MARKET = "USDT"


def _minimal_account(*, btc_total: str = "0.01") -> protocol_models.CopiedAccount:
    total = float(decimal.Decimal(btc_total))
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=time.time(),
        copied_assets=[
            protocol_models.CopiedAsset(name="BTC", total=total, available=total, ratio=1.0),
        ],
    )


class TestUpdateActionTradingSignalIfRelevant:
    def test_updates_reference_account_when_strategy_matches(self):
        original_account = _minimal_account(btc_total="0.01")
        action = actions_factory.create_copy_exchange_account_action(
            STRATEGY_ID,
            REFERENCE_MARKET,
            original_account,
            None,
        )
        action.id = "action_copy_exchange_account"
        original_script = action.dsl_script
        new_account = _minimal_account(btc_total="0.99")
        signal = octobot_flow.entities.TradingSignal(
            strategy_id=STRATEGY_ID,
            account=new_account,
        )
        account_copy_util.update_action_trading_signal_if_relevant(
            action, signal, REFERENCE_MARKET
        )
        assert action.dsl_script != original_script
        assert action.dsl_script == action.resolved_dsl_script
        assert action.id == "action_copy_exchange_account"
        assert "0.99" in action.dsl_script
        assert "0.01" not in action.dsl_script

    def test_raises_when_strategy_id_mismatches(self):
        action = actions_factory.create_copy_exchange_account_action(
            STRATEGY_ID,
            REFERENCE_MARKET,
            _minimal_account(),
            None,
        )
        action.id = "a1"
        signal = octobot_flow.entities.TradingSignal(
            strategy_id="other-strategy",
            account=_minimal_account(btc_total="2"),
        )
        with pytest.raises(octobot_flow.errors.CommunityTradingSignalError):
            account_copy_util.update_action_trading_signal_if_relevant(
                action, signal, REFERENCE_MARKET
            )

    def test_no_op_when_top_is_not_copy_exchange_account(self):
        action = octobot_flow.entities.DSLScriptActionDetails(
            id="lit",
            dsl_script="42",
            resolved_dsl_script="42",
        )
        signal = octobot_flow.entities.TradingSignal(
            strategy_id=STRATEGY_ID,
            account=_minimal_account(),
        )
        account_copy_util.update_action_trading_signal_if_relevant(
            action, signal, REFERENCE_MARKET
        )
        assert action.dsl_script == "42"

    def test_no_op_for_non_dsl_action(self):
        action = octobot_flow.entities.ConfiguredActionDetails(
            id="cfg",
            action="apply_configuration",
            config={},
        )
        signal = octobot_flow.entities.TradingSignal(
            strategy_id=STRATEGY_ID,
            account=_minimal_account(),
        )
        account_copy_util.update_action_trading_signal_if_relevant(
            action, signal, REFERENCE_MARKET
        )
        assert action.action == "apply_configuration"

    def test_raises_when_dsl_script_empty(self):
        action = octobot_flow.entities.DSLScriptActionDetails(
            id="x",
            dsl_script="",
            resolved_dsl_script="",
        )
        signal = octobot_flow.entities.TradingSignal(
            strategy_id=STRATEGY_ID,
            account=_minimal_account(),
        )
        with pytest.raises(octobot_flow.errors.InvalidAutomationActionError):
            account_copy_util.update_action_trading_signal_if_relevant(
                action, signal, REFERENCE_MARKET
            )

    def test_raises_when_unresolved_placeholder(self):
        action = octobot_flow.entities.DSLScriptActionDetails(
            id="x",
            dsl_script=(
                f"copy_exchange_account(strategy_id={json.dumps(STRATEGY_ID)}, "
                f"reference_market='{REFERENCE_MARKET}', "
                f"reference_account='{commons_constants.UNRESOLVED_PARAMETER_PLACEHOLDER}', "
                f"account_copy_settings='{{}}')"
            ),
            resolved_dsl_script="",
        )
        signal = octobot_flow.entities.TradingSignal(
            strategy_id=STRATEGY_ID,
            account=_minimal_account(),
        )
        with pytest.raises(octobot_flow.errors.UnresolvedDSLScriptError):
            account_copy_util.update_action_trading_signal_if_relevant(
                action, signal, REFERENCE_MARKET
            )

    def test_raises_on_unknown_operator(self):
        action = octobot_flow.entities.DSLScriptActionDetails(
            id="x",
            dsl_script="not_a_registered_dsl_operator_xyz_123()",
            resolved_dsl_script="",
        )
        signal = octobot_flow.entities.TradingSignal(
            strategy_id=STRATEGY_ID,
            account=_minimal_account(),
        )
        with pytest.raises(commons_errors.UnsupportedOperatorError):
            account_copy_util.update_action_trading_signal_if_relevant(
                action, signal, REFERENCE_MARKET
            )
