#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import json

import dbos
import mock
import pytest
import octobot_node.models as node_models
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_node.scheduler.workflows_util as workflows_util

_PARENT_WORKFLOW_ID = "741ce171-dac9-40be-83dc-b443c0eaf0e2"


def _child_workflow_id(child_index: int) -> str:
    if child_index == 0:
        return _PARENT_WORKFLOW_ID
    return f"{_PARENT_WORKFLOW_ID}_{child_index}"


def _workflow_status_row(
    *,
    workflow_id: str,
    updated_at: int = 0,
    status: str = dbos.WorkflowStatusString.ENQUEUED.value,
) -> mock.Mock:
    workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
    workflow_status.workflow_id = workflow_id
    workflow_status.updated_at = updated_at
    workflow_status.status = status
    return workflow_status


def _automation_task_content(*, automation_name: str) -> str:
    return json.dumps(
        {
            workflows_util.STATE_KEY: {
                "automation": {
                    "metadata": {
                        "automation_id": "automation_1",
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
    if output_content is None:
        workflow_status.output = None
    else:
        workflow_status.output = json.dumps(
            workflow_params.AutomationWorkflowOutput(state=output_content).to_dict(
                include_default_values=False
            )
        )
    return workflow_status


class TestParseAutomationChildWorkflowIndex:
    def test_parent_workflow_id_maps_to_zero(self):
        assert workflows_util.parse_automation_child_workflow_index(_PARENT_WORKFLOW_ID) == 0

    def test_underscore_suffix_maps_to_child_index(self):
        assert workflows_util.parse_automation_child_workflow_index(_child_workflow_id(1)) == 1
        assert workflows_util.parse_automation_child_workflow_index(_child_workflow_id(12)) == 12

    def test_hyphen_suffix_maps_to_child_index(self):
        hyphen_child_id = f"{_PARENT_WORKFLOW_ID}-3"
        assert workflows_util.parse_automation_child_workflow_index(hyphen_child_id) == 3

    def test_non_numeric_suffix_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid child workflow suffix format"):
            workflows_util.parse_automation_child_workflow_index(f"{_PARENT_WORKFLOW_ID}_abc")

    def test_multi_segment_hyphen_suffix_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid child workflow suffix format"):
            workflows_util.parse_automation_child_workflow_index(f"{_PARENT_WORKFLOW_ID}-4-4")

    def test_invalid_suffix_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid child workflow suffix format"):
            workflows_util.parse_automation_child_workflow_index(f"{_PARENT_WORKFLOW_ID}abc")


class TestGetLatestChildWorkflow:
    def test_picks_highest_child_suffix_over_newer_updated_at(self):
        finished_child = _workflow_status_row(
            workflow_id=_child_workflow_id(56),
            updated_at=200,
            status=dbos.WorkflowStatusString.SUCCESS.value,
        )
        waiting_child = _workflow_status_row(
            workflow_id=_child_workflow_id(57),
            updated_at=100,
            status=dbos.WorkflowStatusString.ENQUEUED.value,
        )
        chosen = workflows_util.get_latest_child_workflow([finished_child, waiting_child])
        assert chosen.workflow_id == _child_workflow_id(57)

    def test_picks_child_over_parent(self):
        parent_workflow = _workflow_status_row(workflow_id=_child_workflow_id(0), updated_at=50)
        child_workflow = _workflow_status_row(workflow_id=_child_workflow_id(1), updated_at=10)
        chosen = workflows_util.get_latest_child_workflow([parent_workflow, child_workflow])
        assert chosen.workflow_id == _child_workflow_id(1)

    def test_single_element_list_returns_that_workflow(self):
        only_workflow = _workflow_status_row(workflow_id=_child_workflow_id(4), updated_at=1)
        chosen = workflows_util.get_latest_child_workflow([only_workflow])
        assert chosen is only_workflow

    def test_equal_suffix_tie_breaks_on_updated_at(self):
        older_duplicate = _workflow_status_row(workflow_id=_child_workflow_id(5), updated_at=10)
        newer_duplicate = _workflow_status_row(workflow_id=_child_workflow_id(5), updated_at=20)
        chosen = workflows_util.get_latest_child_workflow([older_duplicate, newer_duplicate])
        assert chosen is newer_duplicate

    def test_unparseable_suffix_does_not_win_over_valid_child(self):
        unrelated_workflow = _workflow_status_row(
            workflow_id=f"{_PARENT_WORKFLOW_ID}-4-4",
            updated_at=999,
        )
        valid_child = _workflow_status_row(
            workflow_id=_child_workflow_id(57),
            updated_at=1,
        )
        chosen = workflows_util.get_latest_child_workflow([unrelated_workflow, valid_child])
        assert chosen.workflow_id == _child_workflow_id(57)


class TestGetLatestWorkflow:
    def test_delegates_to_latest_child_workflow(self):
        parent_workflow = _workflow_status_row(workflow_id=_child_workflow_id(0), updated_at=100)
        child_workflow = _workflow_status_row(workflow_id=_child_workflow_id(2), updated_at=1)
        chosen = workflows_util.get_latest_workflow([parent_workflow, child_workflow])
        assert chosen.workflow_id == _child_workflow_id(2)


class TestGetResolvedAutomationTask:
    def test_pending_workflow_uses_input_task_content(self):
        input_content = _automation_task_content(automation_name="from-input")
        output_content = _automation_task_content(automation_name="from-output")
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.PENDING.value,
            input_content=input_content,
            output_content=output_content,
        )

        resolved_task = workflows_util.get_resolved_automation_task(workflow_status)

        assert resolved_task is not None
        assert resolved_task.content == input_content

    def test_success_workflow_uses_output_state(self):
        input_content = _automation_task_content(automation_name="from-input")
        output_content = _automation_task_content(automation_name="from-output")
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.SUCCESS.value,
            input_content=input_content,
            output_content=output_content,
        )

        resolved_task = workflows_util.get_resolved_automation_task(workflow_status)

        assert resolved_task is not None
        assert resolved_task.content == output_content

    def test_error_workflow_uses_output_state(self):
        input_content = _automation_task_content(automation_name="from-input")
        output_content = _automation_task_content(automation_name="from-output")
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.ERROR.value,
            input_content=input_content,
            output_content=output_content,
        )

        resolved_task = workflows_util.get_resolved_automation_task(workflow_status)

        assert resolved_task is not None
        assert resolved_task.content == output_content


class TestGetAutomationStateDict:
    def test_success_workflow_state_dict_matches_output(self):
        input_content = _automation_task_content(automation_name="from-input")
        output_content = _automation_task_content(automation_name="from-output")
        workflow_status = _workflow_status_with_automation_task(
            status=dbos.WorkflowStatusString.SUCCESS.value,
            input_content=input_content,
            output_content=output_content,
        )

        state_dict = workflows_util.get_automation_state_dict(workflow_status)

        assert state_dict is not None
        assert state_dict["automation"]["metadata"]["name"] == "from-output"
