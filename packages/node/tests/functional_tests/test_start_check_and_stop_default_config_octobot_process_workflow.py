#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import asyncio
import os
import shutil
import time
import typing

import mock
import pytest

import octobot.constants as octobot_constants_module
import octobot_protocol.models as octobot_protocol_models
import octobot_commons.process_util as process_util_module

from .util import authenticator_mocks as authenticator_mocks_module
from .util import octobot_process_workflow as octobot_process_workflow_module
from .util import user_action_assertions as user_action_assertions_module
from .util import workflow_common as workflow_common_module

import octobot.community.authentication as community_authentication_module
import octobot_node.config
import octobot_node.scheduler
import octobot_node.scheduler.workflows_util as workflows_util_module

from tests.scheduler import temp_dbos_scheduler

_T_ENQUEUE_SECONDS = 30.0
_T_INIT_SECONDS = 60.0
_T_STOP_SEND_SECONDS = 30.0
_T_STOP_COMPLETE_SECONDS = 45.0

_GENERIC_PROCESS_ACCOUNT_ID = "functional_generic_process_account"
_GENERIC_PROCESS_AUTOMATION_NAME = "test_generic_process_default_config_automation"


class TestStartCheckAndStopDefaultConfigOctobotProcessWorkflow:
    @pytest.mark.asyncio
    async def test_generic_process_default_config_lifecycle(self, temp_dbos_scheduler, monkeypatch):
        if not os.path.isfile(os.path.join(os.getcwd(), "start.py")):
            pytest.skip("start.py missing: run pytest with cwd set to the OctoBot project root")

        non_trading_profile_json = os.path.join(
            os.getcwd(),
            "user",
            "profiles",
            "non-trading",
            "profile.json",
        )
        if not os.path.isfile(non_trading_profile_json):
            pytest.skip("non-trading profile missing under OctoBot user/profiles")

        monkeypatch.setenv(octobot_constants_module.ENV_PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS, "5")

        user_id = workflow_common_module.SIMULATOR_GRID_TEST_COMMUNITY_USER_ID
        protocol_account = workflow_common_module.protocol_account_for_functional(
            account_id=_GENERIC_PROCESS_ACCOUNT_ID,
            usdc_total=1000.0,
            account_name="Generic process functional account",
        )
        create_user_action = octobot_process_workflow_module.build_create_generic_process_user_action(
            account_id=_GENERIC_PROCESS_ACCOUNT_ID,
            name=_GENERIC_PROCESS_AUTOMATION_NAME,
        )
        authentication_instance = authenticator_mocks_module.build_community_authentication(
            workflow_common_module.SIMULATOR_GRID_TEST_PRIVATE_KEY,
            workflow_common_module.SIMULATOR_GRID_TEST_WALLET_PASSPHRASE,
        )

        child_user_root: str | None = None
        child_log_folder: str | None = None
        child_pid: int | None = None

        with (
            mock.patch.object(
                community_authentication_module.CommunityAuthentication,
                "instance",
                return_value=authentication_instance,
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
                        return_value=octobot_process_workflow_module.seeded_generic_process_strategy_for_functional_wallet(),
                    ),
                ),
            ),
            mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", None),
            mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", None),
        ):
            try:
                await asyncio.wait_for(
                    workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        create_user_action,
                        user_id,
                    ),
                    timeout=_T_ENQUEUE_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action timed out enqueueing automation workflow") from exc

            await user_action_assertions_module.assert_user_action_selector_completed_automation_create(
                user_id=user_id,
                user_action_id=create_user_action.id,
                expected_workflow_id=None,
            )
            metadata_automation_id = user_action_assertions_module.resolve_create_automation_metadata_id(
                create_user_action,
            )
            parent_automation_id = await user_action_assertions_module.get_created_automation_id_from_user_action(
                user_id=user_id,
                user_action_id=create_user_action.id,
            )

            inner_state = await octobot_process_workflow_module.wait_for_init_state_ok(
                temp_dbos_scheduler,
                metadata_automation_id,
                timeout_sec=_T_INIT_SECONDS,
            )
            assert inner_state.get("pid")
            child_pid = int(inner_state["pid"])
            assert process_util_module.pid_is_running(child_pid)
            child_user_root = inner_state.get("user_root")
            child_log_folder = inner_state.get("log_folder")

            workflow_rows = await temp_dbos_scheduler.INSTANCE.list_workflows_async()
            workflow_row_matching: typing.Any = None
            state_reader_matching: typing.Any = None
            for workflow_row in workflow_rows:
                if workflows_util_module.get_automation_id(workflow_row) != metadata_automation_id:
                    continue
                state_reader = workflows_util_module.get_automation_state_reader(workflow_row)
                if state_reader is None:
                    continue
                workflow_row_matching = workflow_row
                state_reader_matching = state_reader
                break
            assert state_reader_matching is not None

            protocol_automation = await workflow_common_module.load_protocol_automation_state_for_workflow(
                user_id,
                workflow_row_matching,
            )
            assert protocol_automation.status == octobot_protocol_models.WorkflowStatus.RUNNING

            stop_user_action = workflow_common_module.build_stop_user_action(
                automation_id=parent_automation_id,
                user_action_id=f"ua-stop-{create_user_action.id}",
            )
            try:
                await asyncio.wait_for(
                    workflow_common_module.enqueue_user_action_workflow_and_await_terminal_result(
                        temp_dbos_scheduler,
                        stop_user_action,
                        user_id,
                    ),
                    timeout=_T_STOP_SEND_SECONDS,
                )
            except TimeoutError as exc:
                raise AssertionError("execute_user_action timed out enqueueing automation stop") from exc

            stop_assert_deadline = time.monotonic() + _T_STOP_COMPLETE_SECONDS
            while time.monotonic() < stop_assert_deadline:
                listed_user_actions = await octobot_node.scheduler.SCHEDULER.list_user_actions(user_id)
                latest_by_id = user_action_assertions_module.merge_user_actions_latest_per_id(listed_user_actions)
                stop_row = latest_by_id.get(stop_user_action.id)
                if stop_row is not None and stop_row.status == octobot_protocol_models.UserActionStatus.COMPLETED:
                    break
                await asyncio.sleep(workflow_common_module.DEFAULT_WORKFLOW_POLL_INTERVAL_SECONDS)
            else:
                await user_action_assertions_module.assert_user_action_selector_completed_automation_stop(
                    user_id=user_id,
                    user_action_id=stop_user_action.id,
                )

            await workflow_common_module.wait_for_stop_success_output(
                temp_dbos_scheduler,
                metadata_automation_id,
                _T_STOP_COMPLETE_SECONDS,
            )

            protocol_automation_after_stop = await workflow_common_module.load_protocol_automation_state_for_workflow(
                user_id,
                workflow_row_matching,
            )
            assert protocol_automation_after_stop.status == octobot_protocol_models.WorkflowStatus.COMPLETED

            stop_deadline = time.monotonic() + octobot_process_workflow_module.CHILD_STOP_WAIT_SEC
            while time.monotonic() < stop_deadline:
                if child_pid is not None and not process_util_module.pid_is_running(child_pid):
                    break
                await asyncio.sleep(0.5)
            else:
                pytest.fail(f"expected child pid {child_pid} to exit after AUTOMATION_STOP")

        if child_user_root and os.path.isdir(child_user_root):
            shutil.rmtree(child_user_root, ignore_errors=True)
        if child_log_folder and os.path.isdir(child_log_folder):
            shutil.rmtree(child_log_folder, ignore_errors=True)
