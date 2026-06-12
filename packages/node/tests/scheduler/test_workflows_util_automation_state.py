#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import json

import dbos
import mock
import octobot_node.models as node_models
import octobot_node.scheduler.workflows.params as workflow_params
import octobot_node.scheduler.workflows_util as workflows_util


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
