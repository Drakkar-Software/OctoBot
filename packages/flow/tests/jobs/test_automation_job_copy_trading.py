import json
import mock
import pytest
import time

import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.jobs.automation_job as automation_job_module
import octobot_flow.logic.configuration
import octobot_flow.repositories.community


STRATEGY_ID = "9192736c-missing-signal-strategy"


def _empty_copy_action(strategy_id: str = STRATEGY_ID) -> octobot_flow.entities.DSLScriptActionDetails:
    return octobot_flow.entities.DSLScriptActionDetails(
        id="action_copy_exchange_account",
        dsl_script=(
            f"copy_exchange_account(strategy_id={json.dumps(strategy_id)}, "
            f"reference_market='', reference_account='')"
        ),
        resolved_dsl_script=(
            f"copy_exchange_account(strategy_id={json.dumps(strategy_id)}, "
            f"reference_market='', reference_account='')"
        ),
    )


def _minimal_automation_job() -> automation_job_module.AutomationJob:
    automation_state = {
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {"actions": []},
        }
    }
    auth_details = octobot_flow.entities.UserAuthentication(wallet_address="0xtest")
    return automation_job_module.AutomationJob(automation_state, [], [], auth_details)


class TestInitAllRequiredCopyTradingData:
    @pytest.mark.asyncio
    async def test_raises_when_required_strategy_signal_is_missing(self):
        automation_job = _minimal_automation_job()
        copy_action = _empty_copy_action()
        minimal_profile_data = octobot_flow.logic.configuration.create_profile_data(
            None,
            "automation_1",
            set(),
        )
        community_repository = mock.Mock()
        fetch_trading_signals_mock = mock.AsyncMock(return_value=[])

        with mock.patch.object(
            octobot_flow.repositories.community.TradingSignalsRepository,
            "from_community_repository",
            return_value=mock.Mock(fetch_trading_signals=fetch_trading_signals_mock),
        ):
            with pytest.raises(octobot_flow.errors.CommunityTradingSignalError, match=STRATEGY_ID):
                await automation_job._init_all_required_copy_trading_data(
                    community_repository,
                    [copy_action],
                    minimal_profile_data,
                )

        fetch_trading_signals_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_copy_trading_data_when_signals_are_present(self):
        automation_job = _minimal_automation_job()
        copy_action = _empty_copy_action()
        minimal_profile_data = octobot_flow.logic.configuration.create_profile_data(
            None,
            "automation_1",
            set(),
        )
        trading_signal = octobot_flow.entities.TradingSignal(
            strategy_id=STRATEGY_ID,
            account=protocol_models.CopiedAccount(
                version=copy_constants.COPIED_ACCOUNT_VERSION,
                updated_at=time.time(),
                copied_assets=[],
            ),
        )
        community_repository = mock.Mock()
        fetch_trading_signals_mock = mock.AsyncMock(return_value=[trading_signal])

        with mock.patch.object(
            octobot_flow.repositories.community.TradingSignalsRepository,
            "from_community_repository",
            return_value=mock.Mock(fetch_trading_signals=fetch_trading_signals_mock),
        ):
            copy_trading_data = await automation_job._init_all_required_copy_trading_data(
                community_repository,
                [copy_action],
                minimal_profile_data,
            )

        assert copy_trading_data is not None
        assert copy_trading_data.trading_signals == [trading_signal]
