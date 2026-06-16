#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest
import dbos

import octobot_protocol.models as protocol_models
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler.workflows_util as workflows_util


class TestResolveUserActionWorkflowInputs:
    def test_unwraps_dbos_kwargs_inputs_key(self):
        user_action = protocol_models.UserAction(id="ua-kwargs", configuration=None)
        encoded = params.UserActionWorkflowInputs(
            user_id="0xkwargs",
            user_action=user_action,
        ).to_dict(include_default_values=False)
        workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_status.workflow_id = "wf-kwargs"
        workflow_status.input = {"args": [], "kwargs": {"inputs": encoded}}

        resolved = workflows_util.resolve_user_action_workflow_inputs(workflow_status)

        assert resolved.inputs is not None
        assert resolved.inputs.user_id == "0xkwargs"
        assert resolved.inputs.user_action.id == "ua-kwargs"

    def test_unwraps_portable_json_named_args_inputs(self):
        user_action = protocol_models.UserAction(id="ua-portable", configuration=None)
        encoded = params.UserActionWorkflowInputs(
            user_id="0xportable",
            user_action=user_action,
        ).to_dict(include_default_values=False)
        workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_status.workflow_id = "wf-portable"
        workflow_status.input = {
            "args": [
                {
                    "positionalArgs": [],
                    "namedArgs": {"inputs": encoded},
                },
            ],
            "kwargs": {},
        }

        resolved = workflows_util.resolve_user_action_workflow_inputs(workflow_status)

        assert resolved.inputs is not None
        assert resolved.inputs.user_id == "0xportable"
        assert resolved.inputs.user_action.id == "ua-portable"

    def test_empty_wrappers_report_no_inputs_not_missing_fields(self):
        workflow_status = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_status.workflow_id = "wf-empty"
        workflow_status.input = {
            "args": [{"positionalArgs": [], "namedArgs": {}}],
            "kwargs": {},
        }

        resolved = workflows_util.resolve_user_action_workflow_inputs(workflow_status)

        assert resolved.inputs is None
        assert resolved.parse_error == "no user-action workflow inputs found"
