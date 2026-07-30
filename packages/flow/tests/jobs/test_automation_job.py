import mock
import pytest
import time

import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models

import octobot_flow.entities
import octobot_flow.entities.actions.action_details as action_details
import octobot_flow.errors
import octobot_flow.jobs.automation_job as automation_job_module
import octobot_flow.logic.actions
import octobot_flow.logic.configuration
import octobot_flow.repositories.community

from tests.functionnal_tests import auth_details, global_state


STRATEGY_ID = "test-strategy-id"
_PROCESS_BOUND_DSL_SCRIPT = (
    "run_octobot_process('bots/b1', user_id='user_1', waiting_time=1.0, ping_timeout=30.0)"
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


def _dsl_action(dsl_script: str, *, action_id: str = "action_dsl") -> action_details.DSLScriptActionDetails:
    return action_details.DSLScriptActionDetails(
        id=action_id,
        dsl_script=dsl_script,
        dependencies=[],
        resolved_dsl_script=dsl_script,
    )


def _automation_job_with_exchange_dag(
    *dag_actions: action_details.AbstractActionDetails,
) -> automation_job_module.AutomationJob:
    automation_state = octobot_flow.entities.AutomationState.from_dict(
        {
            "exchange_account_details": {
                "exchange_details": {"internal_name": "binanceus"},
                "auth_details": {},
                "portfolio": {},
            },
            "automation": {
                "metadata": {"automation_id": "automation_1"},
                "actions_dag": {"actions": []},
            },
        }
    )
    automation_state.automation.actions_dag.actions = list(dag_actions)
    user_auth_details = octobot_flow.entities.UserAuthentication(wallet_address="0xtest")
    return automation_job_module.AutomationJob(
        automation_state.to_dict(include_default_values=False),
        [],
        [],
        user_auth_details,
    )


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


class TestFetchDependencies:
    @pytest.mark.asyncio
    async def test_sets_skip_exchange_when_executable_dag_is_process_bound_only(self):
        process_bound_action = _dsl_action(_PROCESS_BOUND_DSL_SCRIPT, action_id="action_run")
        automation_job = _automation_job_with_exchange_dag(process_bound_action)

        fetched_dependencies = await automation_job._fetch_dependencies(
            None,
            [process_bound_action],
        )

        assert fetched_dependencies.skip_exchange is True
        assert fetched_dependencies.fetched_exchange_data is None
        assert fetched_dependencies.fetched_copy_trading_data is None

    @pytest.mark.asyncio
    async def test_does_not_set_skip_exchange_when_no_executable_dag_actions(self):
        completed_process_action = _dsl_action(_PROCESS_BOUND_DSL_SCRIPT, action_id="action_run")
        completed_process_action.executed_at = time.time()
        stop_automation_action = _dsl_action("stop_automation()", action_id="action_stop")
        automation_job = _automation_job_with_exchange_dag(completed_process_action)

        fetched_dependencies = await automation_job._fetch_dependencies(
            None,
            [stop_automation_action],
        )

        assert fetched_dependencies.skip_exchange is False


class TestRequiresInitializationRun:
    def _automation_job_without_exchange(
        self,
        *dag_actions: action_details.AbstractActionDetails,
    ) -> automation_job_module.AutomationJob:
        automation_state = octobot_flow.entities.AutomationState.from_dict(
            {
                "automation": {
                    "metadata": {"automation_id": "automation_1"},
                    "actions_dag": {"actions": []},
                },
            }
        )
        automation_state.automation.actions_dag.actions = list(dag_actions)
        user_auth_details = octobot_flow.entities.UserAuthentication(wallet_address="0xtest")
        return automation_job_module.AutomationJob(
            automation_state.to_dict(include_default_values=False),
            [],
            [],
            user_auth_details,
        )

    def test_skips_initialization_for_process_bound_dag_without_exchange(self):
        process_bound_action = _dsl_action(_PROCESS_BOUND_DSL_SCRIPT, action_id="action_run")
        automation_job = self._automation_job_without_exchange(process_bound_action)
        assert automation_job.is_initialization_run is False

    def test_requires_initialization_for_non_process_bound_dag_without_exchange(self):
        stop_automation_action = _dsl_action("stop_automation()", action_id="action_stop")
        automation_job = self._automation_job_without_exchange(stop_automation_action)
        assert automation_job.is_initialization_run is True

    def test_requires_initialization_for_pending_apply_configuration_without_exchange(self):
        init_action = action_details.ConfiguredActionDetails(
            id="action_init",
            action=octobot_flow.enums.ActionType.APPLY_CONFIGURATION.value,
            config={
                "automation": {
                    "metadata": {"automation_id": "automation_1"},
                },
            },
        )
        process_bound_action = _dsl_action(_PROCESS_BOUND_DSL_SCRIPT, action_id="action_run")
        process_bound_action.dependencies = [
            {
                octobot_flow.enums.ActionDependencyParameter.ACTION_ID.value: init_action.id,
            }
        ]
        automation_job = self._automation_job_without_exchange(init_action, process_bound_action)
        assert automation_job.is_initialization_run is True


class TestGetActionsToExecuteWithStaleCompletedPriority:
    def _automation_job_with_priority_actions(
        self,
        priority_actions: list[action_details.AbstractActionDetails],
        *,
        persisted_priority_actions: list[action_details.AbstractActionDetails] | None = None,
        dag_actions: list[action_details.AbstractActionDetails] | None = None,
    ) -> automation_job_module.AutomationJob:
        automation_state = octobot_flow.entities.AutomationState.from_dict(
            {
                "automation": {
                    "metadata": {"automation_id": "automation_1"},
                    "actions_dag": {"actions": []},
                    "execution": {"previous_execution": {"triggered_at": 1.0}},
                },
                "priority_actions": persisted_priority_actions or [],
            }
        )
        if dag_actions is not None:
            automation_state.automation.actions_dag.actions = list(dag_actions)
        user_auth_details = octobot_flow.entities.UserAuthentication(wallet_address="0xtest")
        return automation_job_module.AutomationJob(
            automation_state.to_dict(include_default_values=False),
            priority_actions,
            [],
            user_auth_details,
        )

    def test_returns_fresh_priority_when_stale_completed_exists(self):
        completed_stop_action = _dsl_action(
            "stop_automation()",
            action_id="action_stop_priority_ua-stop-auto-1-stale",
        )
        completed_stop_action.executed_at = time.time()
        fresh_stop_action = _dsl_action(
            "stop_automation()",
            action_id="action_stop_priority_ua-stop-auto-1-fresh",
        )
        process_bound_action = _dsl_action(_PROCESS_BOUND_DSL_SCRIPT, action_id="action_run")
        automation_job = self._automation_job_with_priority_actions(
            [fresh_stop_action],
            persisted_priority_actions=[completed_stop_action],
            dag_actions=[process_bound_action],
        )

        selected_actions, are_priority_actions = automation_job._get_actions_to_execute()

        assert are_priority_actions is True
        assert len(selected_actions) == 1
        assert selected_actions[0].id == fresh_stop_action.id


class TestRunRaisesWhenSuppliedPriorityAlreadyCompleted:
    @pytest.mark.asyncio
    async def test_raises_pending_priority_actions_skipped_error(self):
        completed_stop_action = _dsl_action(
            "stop_automation()",
            action_id="action_stop_priority_ua-stop-1",
        )
        completed_stop_action.executed_at = time.time()
        process_bound_action = _dsl_action(_PROCESS_BOUND_DSL_SCRIPT, action_id="action_run")
        automation_state = octobot_flow.entities.AutomationState.from_dict(
            {
                "automation": {
                    "metadata": {"automation_id": "automation_1"},
                    "actions_dag": {"actions": []},
                    "execution": {"previous_execution": {"triggered_at": 1.0}},
                },
                "priority_actions": [completed_stop_action],
            }
        )
        automation_state.automation.actions_dag.actions = [process_bound_action]
        user_auth_details = octobot_flow.entities.UserAuthentication()
        automation_job = automation_job_module.AutomationJob(
            automation_state.to_dict(include_default_values=False),
            [completed_stop_action],
            [],
            user_auth_details,
        )

        with pytest.raises(octobot_flow.errors.PendingPriorityActionsSkippedError):
            await automation_job.run()
