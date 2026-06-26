import mock
import pytest
import time

import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models

import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.jobs.automation_job as automation_job_module
import octobot_flow.logic.actions
import octobot_flow.logic.configuration
import octobot_flow.repositories.community

from tests.functionnal_tests import auth_details, global_state


STRATEGY_ID = "test-strategy-id"


def _minimal_automation_job() -> automation_job_module.AutomationJob:
    automation_state = {
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {"actions": []},
        }
    }
    auth_details = octobot_flow.entities.UserAuthentication(wallet_address="0xtest")
    return automation_job_module.AutomationJob(automation_state, [], [], auth_details)


def _minimal_copied_account() -> protocol_models.CopiedAccount:
    return protocol_models.CopiedAccount(
        version=copy_constants.COPIED_ACCOUNT_VERSION,
        updated_at=time.time(),
        copied_assets=[],
    )


class TestValidateInput:
    @pytest.mark.asyncio
    async def test_not_automations_configured(
        self,
        global_state: dict,
        auth_details: octobot_flow.entities.UserAuthentication,
    ):
        global_state["automation"] = {}
        with pytest.raises(octobot_flow.errors.NoAutomationError):
            async with automation_job_module.AutomationJob(global_state, [], [], auth_details):
                pass


class TestEmitTradingSignals:
    @pytest.mark.asyncio
    async def test_skips_emission_and_logs_when_wallet_not_found(self):
        automation_job = _minimal_automation_job()
        automation = automation_job.automation_state.automation
        automation.metadata.strategy_id = STRATEGY_ID
        automation.exchange_account_elements = octobot_flow.entities.ExchangeAccountElements()
        fetched_dependencies = octobot_flow.entities.FetchedDependencies()
        community_repository = mock.Mock()
        wallet_error = wallet_backend_errors.WalletNotFoundError("Wallet not found")
        insert_trading_signal_mock = mock.AsyncMock(side_effect=wallet_error)
        copied_account = _minimal_copied_account()

        with mock.patch.object(
            octobot_flow.repositories.community.TradingSignalsRepository,
            "from_community_repository",
            return_value=mock.Mock(insert_trading_signal=insert_trading_signal_mock),
        ), mock.patch.object(
            octobot_flow.logic.configuration,
            "infer_reference_market",
            return_value="USDT",
        ), mock.patch.object(
            octobot_flow.logic.actions,
            "reference_exchange_elements_to_account",
            return_value=copied_account,
        ), mock.patch.object(
            automation_job._logger,
            "error",
        ) as error_log_mock:
            await automation_job._emit_trading_signals(
                community_repository,
                automation,
                fetched_dependencies,
            )

        insert_trading_signal_mock.assert_awaited_once()
        emitted_signal = insert_trading_signal_mock.await_args.args[0]
        assert emitted_signal.strategy_id == STRATEGY_ID
        assert emitted_signal.account is copied_account
        error_log_mock.assert_called_once_with(f"Skipping trading signal emission: {wallet_error}")
