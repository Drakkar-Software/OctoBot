#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import json

import dbos
import mock
import pytest

import octobot_protocol.models as protocol_models
import octobot_node.models as node_models
import octobot_node.protocol.automations as automations_protocol
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader_module
import octobot_node.scheduler.workflows.params as workflow_params


_PARENT_WORKFLOW_ID = "741ce171-dac9-40be-83dc-b443c0eaf0e2"
_LOADER_PARENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _automation_task_content(*, automation_name: str, automation_id: str = "automation_1") -> str:
    return json.dumps(
        {
            automation_states_loader_module.STATE_KEY: {
                "automation": {
                    "metadata": {
                        "automation_id": automation_id,
                        "name": automation_name,
                    },
                    "actions_dag": {"actions": []},
                    "execution": {},
                },
            },
        }
    )


def _workflow_status_with_automation_task(
    *,
    status: str,
    input_content: str,
    output_content: str | None = None,
) -> mock.Mock:
    task = node_models.Task(
        name="automation-task",
        content=input_content,
        type=node_models.TaskType.EXECUTE_ACTIONS.value,
    )
    encoded_inputs = workflow_params.AutomationWorkflowInputs(task=task).to_dict(
        include_default_values=False
    )
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = "parent-workflow-id_1"
    workflow_status.status = status
    workflow_status.input = {"args": [encoded_inputs], "kwargs": {}}
    workflow_status.error = None
    if output_content is None:
        workflow_status.output = None
    else:
        workflow_status.output = json.dumps(
            workflow_params.AutomationWorkflowOutput(state=output_content).to_dict(
                include_default_values=False
            )
        )
    return workflow_status


def _running_automation_task_content() -> str:
    state_dict = {
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {
                "actions": [{"id": "a1", "dsl_script": "True"}],
            },
            "execution": {
                "current_execution": {"scheduled_to": 1, "triggered_at": 2},
            },
        },
    }
    return json.dumps({"state": state_dict})


def _build_mock_workflow_status(
    task: node_models.Task,
    encrypted_state: str,
    state_metadata: str,
    workflow_id: str = _LOADER_PARENT_ID,
) -> mock.Mock:
    output = workflow_params.AutomationWorkflowOutput(state=encrypted_state, state_metadata=state_metadata)
    inputs = workflow_params.AutomationWorkflowInputs(task=task, execution_time=0)
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = workflow_id
    workflow_status.name = "test-task"
    workflow_status.status = dbos.WorkflowStatusString.SUCCESS.value
    workflow_status.output = json.dumps(output.to_dict())
    workflow_status.input = {"args": [inputs.to_dict()], "kwargs": {}}
    workflow_status.created_at = None
    workflow_status.updated_at = None
    workflow_status.error = None
    return workflow_status


def _build_mock_workflow_status_error(
    task: node_models.Task,
    error: Exception,
    workflow_id: str = _LOADER_PARENT_ID,
) -> mock.Mock:
    inputs = workflow_params.AutomationWorkflowInputs(task=task, execution_time=0)
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = workflow_id
    workflow_status.name = "test-task"
    workflow_status.status = dbos.WorkflowStatusString.ERROR.value
    workflow_status.output = None
    workflow_status.error = error
    workflow_status.input = {"args": [inputs.to_dict()], "kwargs": {}}
    workflow_status.created_at = None
    workflow_status.updated_at = 2
    return workflow_status


class TestGetAutomationStateDict:
    def test_success_workflow_state_dict_matches_output(self):
        input_content = _automation_task_content(automation_name="from-input")
        output_content = _automation_task_content(automation_name="from-output")
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.SUCCESS.value,
            input_content=input_content,
            output_content=output_content,
        )

        state_dict = automation_states_loader_module.get_automation_state_dict(workflow_status)

        assert state_dict is not None
        assert state_dict["automation"]["metadata"]["name"] == "from-output"


class TestPatchTaskContentDegradedState:
    def test_persists_degraded_state_in_task_content(self):
        task_content = _automation_task_content(automation_name="copy-grid")

        patched_content = automation_states_loader_module.patch_task_content_degraded_state(
            task_content,
            "not_enough_funds",
            "Insufficient funds",
            since=1234.5,
        )

        degraded_state = json.loads(patched_content)["state"]["automation"]["execution"]["degraded_state"]
        assert degraded_state == {
            "since": 1234.5,
            "error": "not_enough_funds",
            "reason": "Insufficient funds",
        }

    def test_preserves_existing_degraded_since_on_subsequent_patch(self):
        task_content = _automation_task_content(automation_name="copy-grid")
        task_content = automation_states_loader_module.patch_task_content_degraded_state(
            task_content,
            "not_enough_funds",
            "Insufficient funds",
            since=1000.0,
        )

        patched_content = automation_states_loader_module.patch_task_content_degraded_state(
            task_content,
            "invalid_order",
            "Order volume below exchange minimum",
            since=2000.0,
        )

        degraded_state = json.loads(patched_content)["state"]["automation"]["execution"]["degraded_state"]
        assert degraded_state == {
            "since": 1000.0,
            "error": "invalid_order",
            "reason": "Order volume below exchange minimum",
        }


class TestGetAutomationId:
    def test_returns_metadata_automation_id(self):
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.PENDING.value,
            input_content=_automation_task_content(
                automation_name="dca",
                automation_id="automation-dca",
            ),
        )

        assert automation_states_loader_module.get_automation_id(workflow_status) == "automation-dca"


class TestGetAutomationStateReader:
    def test_reader_exposes_automation_name(self):
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.PENDING.value,
            input_content=_automation_task_content(automation_name="grid-bot"),
        )

        state_reader = automation_states_loader_module.get_automation_state_reader(workflow_status)

        assert state_reader is not None
        state_dict = automation_states_loader_module.get_automation_state_dict(workflow_status)
        assert state_dict is not None
        assert state_dict["automation"]["metadata"]["name"] == "grid-bot"

    def test_copied_strategy_ids_empty_when_none_configured(self):
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.PENDING.value,
            input_content=_automation_task_content(automation_name="grid-bot"),
        )

        assert automation_states_loader_module.get_automation_copied_strategy_ids(workflow_status) == []


class TestParseFlowAutomationState:
    def test_parses_task_content_into_flow_automation_state(self):
        task = node_models.Task(
            name="automation-task",
            content=_automation_task_content(automation_name="parsed-bot"),
            type=node_models.TaskType.EXECUTE_ACTIONS.value,
        )

        flow_automation_state = automation_states_loader_module.parse_flow_automation_state(task)

        assert flow_automation_state.automation.metadata.automation_id == "automation_1"


class TestLoadFlowAutomationStatesById:
    @pytest.mark.asyncio
    async def test_builds_flow_states_from_sources(self):
        task = node_models.Task(
            id=_LOADER_PARENT_ID,
            name="automation-task",
            content=_automation_task_content(automation_name="loaded-bot"),
            type=node_models.TaskType.EXECUTE_ACTIONS.value,
        )
        source = automations_protocol.AutomationStateSource(
            task=task,
            workflow_status=dbos.WorkflowStatusString.PENDING.value,
        )
        with mock.patch.object(
            automation_states_loader_module,
            "load_automation_state_sources",
            new=mock.AsyncMock(return_value=[source]),
        ):
            flow_states_by_id = await automation_states_loader_module.load_flow_automation_states_by_id(
                "wallet-id",
            )

        assert flow_states_by_id[_LOADER_PARENT_ID].automation.metadata.automation_id == "automation_1"


class TestLoadProtocolAutomationStates:
    @pytest.mark.asyncio
    async def test_error_workflow_reports_failed_not_running(self):
        task = node_models.Task(
            id=_LOADER_PARENT_ID,
            name="failed-automation",
            content=_running_automation_task_content(),
            type="execute_actions",
        )
        error_workflow = _build_mock_workflow_status_error(
            task,
            RuntimeError("DBOSUnexpectedStepError"),
        )
        with mock.patch(
            "octobot_node.scheduler.SCHEDULER._get_latest_workflow_for_each_automation",
            new=mock.AsyncMock(return_value=[error_workflow]),
        ):
            automation_states = await automation_states_loader_module.load_protocol_automation_states(None)

        assert len(automation_states) == 1
        assert automation_states[0].id == _LOADER_PARENT_ID
        assert automation_states[0].status == protocol_models.WorkflowStatus.FAILED
        assert "DBOSUnexpectedStepError" in (automation_states[0].error or "")
        assert automation_states[0].error_message is None

    @pytest.mark.asyncio
    async def test_success_workflow_with_output_preserves_metadata_name(self):
        task = node_models.Task(
            id=_LOADER_PARENT_ID,
            name="my-automation",
            content=_running_automation_task_content(),
            type="execute_actions",
        )
        success_workflow = _build_mock_workflow_status(
            task,
            encrypted_state=_running_automation_task_content(),
            state_metadata="",
        )
        with mock.patch(
            "octobot_node.scheduler.SCHEDULER._get_latest_workflow_for_each_automation",
            new=mock.AsyncMock(return_value=[success_workflow]),
        ):
            automation_states = await automation_states_loader_module.load_protocol_automation_states(None)

        assert len(automation_states) == 1
        assert automation_states[0].id == _LOADER_PARENT_ID
        assert automation_states[0].metadata.name == "my-automation"


class TestLoadWalletAutomationStates:
    @pytest.mark.asyncio
    async def test_loads_protocol_and_flow_states_from_single_source_fetch(self):
        task = node_models.Task(
            id=_LOADER_PARENT_ID,
            name="wallet-automation",
            content=_automation_task_content(automation_name="wallet-bot"),
            type=node_models.TaskType.EXECUTE_ACTIONS.value,
        )
        source = automations_protocol.AutomationStateSource(
            task=task,
            workflow_status=dbos.WorkflowStatusString.PENDING.value,
        )
        load_sources_mock = mock.AsyncMock(return_value=[source])
        with mock.patch.object(
            automation_states_loader_module,
            "load_automation_state_sources",
            new=load_sources_mock,
        ):
            wallet_automation_states = await automation_states_loader_module.load_wallet_automation_states(
                "wallet-id",
            )

        load_sources_mock.assert_awaited_once_with("wallet-id", None, load_output=True)
        assert len(wallet_automation_states.protocol_states) == 1
        assert wallet_automation_states.protocol_states[0].id == _LOADER_PARENT_ID
        assert wallet_automation_states.flow_states_by_id[_LOADER_PARENT_ID].automation.metadata.automation_id == "automation_1"


class TestLoadWalletAutomationStatesForTradeSymbols:
    @pytest.mark.asyncio
    async def test_uses_enqueued_pending_statuses_and_skips_workflow_outputs(self):
        get_latest_mock = mock.AsyncMock(return_value=[])
        scheduler_mock = mock.Mock()
        scheduler_mock._get_latest_workflow_for_each_automation = get_latest_mock
        with mock.patch(
            "octobot_node.scheduler.SCHEDULER",
            scheduler_mock,
        ):
            wallet_automation_states = await automation_states_loader_module.load_wallet_automation_states_for_trade_symbols(
                "wallet-id",
            )

        get_latest_mock.assert_awaited_once_with(
            "wallet-id",
            [
                dbos.WorkflowStatusString.ENQUEUED,
                dbos.WorkflowStatusString.PENDING,
            ],
            load_output=False,
        )
        assert wallet_automation_states.protocol_states == []
        assert wallet_automation_states.flow_states_by_id == {}


class TestGetAutomationWorkflowStatus:
    @pytest.mark.asyncio
    async def test_returns_matching_pending_workflow(self):
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.PENDING.value,
            input_content=_automation_task_content(
                automation_name="pending-bot",
                automation_id="automation-pending",
            ),
        )
        with mock.patch.object(
            dbos.DBOS,
            "list_workflows_async",
            new=mock.AsyncMock(return_value=[workflow_status]),
        ):
            resolved_workflow = await automation_states_loader_module.get_automation_workflow_status(
                "automation-pending",
            )

        assert resolved_workflow is workflow_status

    @pytest.mark.asyncio
    async def test_raises_when_no_workflow_matches(self):
        with mock.patch.object(
            dbos.DBOS,
            "list_workflows_async",
            new=mock.AsyncMock(return_value=[]),
        ):
            with pytest.raises(ValueError, match="No automation workflow found"):
                await automation_states_loader_module.get_automation_workflow_status("missing-automation")
