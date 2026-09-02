import asyncio
import datetime
import tempfile

import mock
import pytest

import octobot_node.constants as octobot_node_constants
import octobot_node.errors as node_errors
import octobot_sync.server as sync_server_module
import octobot_node.scheduler
import octobot_node.scheduler.api as scheduler_api
import octobot_node.scheduler.tasks as scheduler_tasks
import octobot_protocol.models as protocol_models

import tests.scheduler as scheduler_tests

_TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TEST_USER_ID = sync_server_module.derive_user_id(_TEST_PRIVATE_KEY)
_MISSING_AUTOMATION_ID = "functional-missing-automation-workflow"
_WORKFLOW_RESULT_TIMEOUT_SECONDS = 120.0


@pytest.fixture
def patched_user_action_workflow_max_iteration_retries():
    with mock.patch.object(octobot_node_constants, "USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES", 2):
        yield


@pytest.fixture
def temp_dbos_scheduler_signal_automation_user_action(
    patched_user_action_workflow_max_iteration_retries,  # noqa: ARG001
):
    with tempfile.NamedTemporaryFile() as temp_file:
        dbos_runtime = scheduler_tests.init_scheduler(temp_file.name)
        dbos_runtime.reset_system_database()
        dbos_runtime.launch()
        try:
            yield octobot_node.scheduler.SCHEDULER
        finally:
            dbos_runtime.destroy()


def _wrap_configuration(payload) -> protocol_models.UserActionConfiguration:
    return protocol_models.UserActionConfiguration.from_json(payload.to_json())


def _build_forced_trigger_signal_user_action(
    *,
    user_action_id: str,
    automation_id: str,
) -> protocol_models.UserAction:
    sample_timestamp = datetime.datetime(2026, 5, 1, 12, 0, 0, tzinfo=datetime.UTC)
    payload = protocol_models.SignalAutomationConfiguration(
        action_type=protocol_models.UserActionType.AUTOMATION_SIGNAL,
        automation_id=automation_id,
        signal_type=protocol_models.AutomationSignalType.FORCED_TRIGGER,
    )
    return protocol_models.UserAction(
        id=user_action_id,
        status=protocol_models.UserActionStatus.PENDING,
        created_at=sample_timestamp,
        updated_at=sample_timestamp,
        configuration=_wrap_configuration(payload),
    )


async def _run_user_action_to_completion(
    user_id: str,
    user_action: protocol_models.UserAction,
) -> str:
    workflow_id = await scheduler_tasks.trigger_user_action_workflow(user_action, user_id)
    workflow_handle = await octobot_node.scheduler.SCHEDULER.INSTANCE.retrieve_workflow_async(workflow_id)
    await asyncio.wait_for(workflow_handle.get_result(), timeout=_WORKFLOW_RESULT_TIMEOUT_SECONDS)
    return workflow_id


@pytest.mark.asyncio
class TestExecuteUserActionSignalAutomationFailureReporting:
    async def test_signal_automation_reports_automation_not_found_when_no_active_workflow(
        self,
        temp_dbos_scheduler_signal_automation_user_action,
    ):
        signal_user_action = _build_forced_trigger_signal_user_action(
            user_action_id="ua-signal-missing-automation",
            automation_id=_MISSING_AUTOMATION_ID,
        )

        await _run_user_action_to_completion(_TEST_USER_ID, signal_user_action)

        listed_user_actions = await scheduler_api.list_user_actions(
            _TEST_USER_ID,
            active_only=True,
        )
        assert len(listed_user_actions) == 1
        listed_user_action = listed_user_actions[0]
        assert listed_user_action.id == signal_user_action.id
        assert listed_user_action.status == protocol_models.UserActionStatus.FAILED
        assert listed_user_action.result is not None
        result_inner = listed_user_action.result.actual_instance
        assert isinstance(result_inner, protocol_models.AutomationActionResult)
        assert result_inner.result_type == protocol_models.UserActionResultType.AUTOMATION
        assert result_inner.error_message == protocol_models.AutomationActionResultErrorMessage.AUTOMATION_NOT_FOUND
        assert result_inner.error_details is not None
        assert _MISSING_AUTOMATION_ID in result_inner.error_details


@pytest.mark.asyncio
class TestExecuteUserActionSignalAutomationExecutionResults:
    async def test_actions_signal_reports_not_enough_funds_on_user_action(
        self,
        temp_dbos_scheduler_signal_automation_user_action,
    ):
        import asyncio

        from .util import grid_workflow as grid_sim_util
        from .util import price_mocks as price_mocks_module
        from .util import workflow_common as workflow_common_module
        from .util import authenticator_mocks as authenticator_mocks_module

        import octobot.community.authentication as community_authentication_module
        import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
        import octobot_node.config as octobot_node_config

        _GRID_ACCOUNT_ID = "functional-signal-not-enough-funds"
        _GRID_AUTOMATION_CONFIGURATION_ID = "d4e5f6a7-b8c9-4012-d345-6789abcdef02"
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        patched_fetch_tickers = price_mocks_module.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE,
        )
        patched_fetch_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_price(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE,
        )
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=_GRID_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Signal not enough funds account",
        )
        create_user_action = grid_sim_util.build_create_grid_user_action(
            account_id=_GRID_ACCOUNT_ID,
            name="signal_not_enough_funds_automation",
            automation_id=_GRID_AUTOMATION_CONFIGURATION_ID,
        )
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )
        with (
            mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
            ),
            mock.patch.object(
                octobot_flow_repositories_exchange_module.TickersRepository,
                "fetch_tickers",
                new=patched_fetch_tickers,
            ),
            mock.patch.object(
                octobot_flow_repositories_exchange_module.OhlcvRepository,
                "fetch_ohlcv",
                side_effect=patched_fetch_ohlcv,
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(return_value=protocol_account),
                    get_exchange_config=mock.Mock(
                        return_value=workflow_common_module.protocol_exchange_config_for_grid_functional(),
                    ),
                ),
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.StrategyProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(
                        return_value=grid_sim_util.seeded_grid_strategy_for_functional_wallet(
                            stored_strategy_id=grid_sim_util.SIMULATOR_GRID_DEFAULT_STRATEGY_ID,
                        ),
                    ),
                ),
            ),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", None),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", None),
        ):
            workflow_common_module.seed_empty_account_trading_state(user_id, _GRID_ACCOUNT_ID)
            await asyncio.wait_for(
                workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                    temp_dbos_scheduler_signal_automation_user_action,
                    create_user_action,
                    user_id,
                ),
                timeout=120.0,
            )
            await workflow_common_module.wait_for_latest_automation_exchange_elements_until(
                temp_dbos_scheduler_signal_automation_user_action,
                _GRID_AUTOMATION_CONFIGURATION_ID,
                lambda elements: grid_sim_util.is_simulator_grid_baseline_exactly_one_trade(
                    *workflow_common_module.buy_sell_trade_counts_from_exchange_elements(elements),
                ),
                workflow_common_module.functional_timeout_seconds(20.0),
                "simulator grid baseline",
                user_id=user_id,
                account_id=_GRID_ACCOUNT_ID,
                require_account_trading_open_orders=True,
            )
            signal_user_action = workflow_common_module.build_actions_signal_user_action(
                automation_id=_GRID_AUTOMATION_CONFIGURATION_ID,
                user_action_id="ua-signal-not-enough-funds",
                signal_payload=[{"script": "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.01"}],
            )
            await _run_user_action_to_completion(user_id, signal_user_action)

        listed_user_actions = await scheduler_api.list_user_actions(user_id, active_only=True)
        listed_user_action = next(
            stored_user_action for stored_user_action in listed_user_actions
            if stored_user_action.id == signal_user_action.id
        )
        assert listed_user_action.status == protocol_models.UserActionStatus.FAILED
        assert listed_user_action.result is not None
        result_inner = listed_user_action.result.actual_instance
        assert isinstance(result_inner, protocol_models.AutomationActionResult)
        assert result_inner.error_message == protocol_models.AutomationActionResultErrorMessage.NOT_ENOUGH_FUNDS
        assert result_inner.signal_execution_results is not None
        assert any(
            priority_action_result.error_status == "not_enough_funds"
            for priority_action_result in result_inner.signal_execution_results
        )

    async def test_actions_signal_reports_execution_timeout_when_callback_missing(
        self,
        temp_dbos_scheduler_signal_automation_user_action,
    ):
        import asyncio

        from .util import grid_workflow as grid_sim_util
        from .util import price_mocks as price_mocks_module
        from .util import signal_bot_workflow as signal_bot_sim_util
        from .util import workflow_common as workflow_common_module
        from .util import authenticator_mocks as authenticator_mocks_module

        import octobot.community.authentication as community_authentication_module
        import octobot_flow.repositories.exchange as octobot_flow_repositories_exchange_module
        import octobot_node.config as octobot_node_config

        _GRID_ACCOUNT_ID = "functional-signal-timeout"
        _GRID_AUTOMATION_CONFIGURATION_ID = "d4e5f6a7-b8c9-4012-d345-6789abcdef03"
        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        patched_fetch_tickers = price_mocks_module.tickers_repository_fetch_tickers_btc_usdc_close_override(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE,
        )
        patched_fetch_ohlcv = price_mocks_module.fetch_ohlcv_side_effect_for_close_price(
            lambda: grid_sim_util.FIXED_BTC_USDC_CLOSE,
        )
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=_GRID_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Signal timeout account",
        )
        create_user_action = grid_sim_util.build_create_grid_user_action(
            account_id=_GRID_ACCOUNT_ID,
            name="signal_timeout_automation",
            automation_id=_GRID_AUTOMATION_CONFIGURATION_ID,
        )
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        with (
            mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
            ),
            mock.patch.object(
                octobot_flow_repositories_exchange_module.TickersRepository,
                "fetch_tickers",
                new=patched_fetch_tickers,
            ),
            mock.patch.object(
                octobot_flow_repositories_exchange_module.OhlcvRepository,
                "fetch_ohlcv",
                side_effect=patched_fetch_ohlcv,
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(return_value=protocol_account),
                    get_exchange_config=mock.Mock(
                        return_value=workflow_common_module.protocol_exchange_config_for_grid_functional(),
                    ),
                ),
            ),
            mock.patch(
                "octobot_sync.sync.collection_providers.StrategyProvider.instance",
                return_value=mock.Mock(
                    get_item=mock.Mock(
                        return_value=grid_sim_util.seeded_grid_strategy_for_functional_wallet(
                            stored_strategy_id=grid_sim_util.SIMULATOR_GRID_DEFAULT_STRATEGY_ID,
                        ),
                    ),
                ),
            ),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", None),
            mock.patch.object(octobot_node_config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", None),
            mock.patch.object(octobot_node_constants, "SIGNAL_EXECUTION_RESULT_TIMEOUT_SECONDS", 0.2),
            mock.patch(
                "octobot_node.scheduler.workflows.user_action_workflow._recv_signal_execution_result",
                side_effect=node_errors.SignalExecutionResultTimeoutError("simulated timeout"),
            ),
        ):
            workflow_common_module.seed_empty_account_trading_state(user_id, _GRID_ACCOUNT_ID)
            await asyncio.wait_for(
                workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                    temp_dbos_scheduler_signal_automation_user_action,
                    create_user_action,
                    user_id,
                ),
                timeout=120.0,
            )
            await signal_bot_sim_util.wait_for_signal_exchange_context_ready(
                temp_dbos_scheduler_signal_automation_user_action,
                _GRID_AUTOMATION_CONFIGURATION_ID,
                user_id,
                workflow_common_module.functional_timeout_seconds(20.0),
            )
            signal_user_action = workflow_common_module.build_actions_signal_user_action(
                automation_id=_GRID_AUTOMATION_CONFIGURATION_ID,
                user_action_id="ua-signal-timeout",
                signal_payload=[{"script": "SYMBOL=BTC/USDC\nSIGNAL=buy\nVOLUME=0.01"}],
            )
            await _run_user_action_to_completion(user_id, signal_user_action)

        listed_user_actions = await scheduler_api.list_user_actions(user_id, active_only=True)
        listed_user_action = next(
            stored_user_action for stored_user_action in listed_user_actions
            if stored_user_action.id == signal_user_action.id
        )
        assert listed_user_action.status == protocol_models.UserActionStatus.FAILED
        result_inner = listed_user_action.result.actual_instance
        assert isinstance(result_inner, protocol_models.AutomationActionResult)
        assert result_inner.error_message == protocol_models.AutomationActionResultErrorMessage.EXECUTION_TIMEOUT
