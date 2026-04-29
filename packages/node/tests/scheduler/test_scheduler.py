#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import json
import mock
import pytest
import dbos

import octobot_commons.cryptography
import octobot_node.config
import octobot_node.models
import octobot_node.scheduler.encryption as encryption
import octobot_node.scheduler.encryption.task_inputs as task_inputs_encryption
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler.scheduler as scheduler_module


def _build_mock_workflow_status(task: octobot_node.models.Task, encrypted_state: str, state_metadata: str, workflow_id: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") -> mock.Mock:
    output = params.AutomationWorkflowOutput(state=encrypted_state, state_metadata=state_metadata)
    inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
    ws = mock.Mock(spec=dbos.WorkflowStatus)
    ws.workflow_id = workflow_id
    ws.name = "test-task"
    ws.status = dbos.WorkflowStatusString.SUCCESS.value
    ws.output = json.dumps(output.to_dict())
    ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
    ws.created_at = None
    ws.updated_at = None
    return ws


def _derive_ecdsa_public_key(ecdsa_private_key: bytes) -> bytes:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
    private = load_pem_private_key(ecdsa_private_key, password=None)
    return private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)


def _make_scheduler_with_mock_instance() -> tuple[scheduler_module.Scheduler, mock.AsyncMock]:
    sched = scheduler_module.Scheduler()
    sched.INSTANCE = mock.AsyncMock()
    return sched, sched.INSTANCE


class TestSchedulerGetResults:

    @pytest.mark.asyncio
    async def test_get_results_returns_plaintext_when_no_user_pub_key(self):
        """When node-side encryption is on but no user RSA public key is set, get_results must
        return the decrypted plaintext state (not the server-encrypted blob)."""
        rsa_private_key, _ = octobot_commons.cryptography.generate_rsa_key_pair(2048)
        ecdsa_private_key, _ = octobot_commons.cryptography.generate_ecdsa_key_pair()

        plaintext_state = json.dumps({"result": "my_output", "value": 42})

        task_inputs_encryption._server_rsa_public_key_bytes.cache_clear()
        task_inputs_encryption._server_ecdsa_public_key_bytes.cache_clear()

        encryption_patches = (
            mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", rsa_private_key),
            mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", ecdsa_private_key),
        )
        with encryption_patches[0], encryption_patches[1]:
            assert octobot_node.config.settings.is_node_side_encryption_enabled is True
            encrypted_state, state_metadata = task_inputs_encryption.encrypt_task_content(plaintext_state)

        task = octobot_node.models.Task(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            name="test-task",
            content=encrypted_state,
            content_metadata=state_metadata,
            type="execute_actions",
            user_rsa_public_key=None,
        )
        ws = _build_mock_workflow_status(task, encrypted_state, state_metadata)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        with encryption_patches[0], encryption_patches[1], \
             mock.patch.object(octobot_node.config.settings, "TASKS_USER_RSA_PUBLIC_KEY", None):
            executions = await sched.get_results()

        assert len(executions) == 1
        execution = executions[0]
        assert execution.result == plaintext_state
        assert execution.result_metadata == ""

    @pytest.mark.asyncio
    async def test_get_results_encrypts_result_with_user_pub_key(self):
        """When node-side encryption is on and a user RSA public key is provided on the task,
        get_results must re-encrypt the result with that key and return non-empty metadata."""
        rsa_private_key, _ = octobot_commons.cryptography.generate_rsa_key_pair(2048)
        ecdsa_private_key, _ = octobot_commons.cryptography.generate_ecdsa_key_pair()
        user_rsa_private_key, user_rsa_public_key = octobot_commons.cryptography.generate_rsa_key_pair(2048)

        plaintext_state = json.dumps({"result": "encrypted_output", "value": 99})

        task_inputs_encryption._server_rsa_public_key_bytes.cache_clear()
        task_inputs_encryption._server_ecdsa_public_key_bytes.cache_clear()

        encryption_patches = (
            mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_RSA_PRIVATE_KEY", rsa_private_key),
            mock.patch.object(octobot_node.config.settings, "TASKS_SERVER_ECDSA_PRIVATE_KEY", ecdsa_private_key),
        )
        with encryption_patches[0], encryption_patches[1]:
            assert octobot_node.config.settings.is_node_side_encryption_enabled is True
            encrypted_state, state_metadata = task_inputs_encryption.encrypt_task_content(plaintext_state)

        task = octobot_node.models.Task(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            name="test-task",
            content=encrypted_state,
            content_metadata=state_metadata,
            type="execute_actions",
            user_rsa_public_key=user_rsa_public_key.decode("utf-8"),
        )
        ws = _build_mock_workflow_status(task, encrypted_state, state_metadata, workflow_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        with encryption_patches[0], encryption_patches[1], \
             mock.patch.object(octobot_node.config.settings, "TASKS_USER_RSA_PUBLIC_KEY", None):
            executions = await sched.get_results()

        assert len(executions) == 1
        execution = executions[0]
        assert execution.result != plaintext_state
        assert execution.result_metadata

        server_ecdsa_public_key = _derive_ecdsa_public_key(ecdsa_private_key)
        decrypted = encryption.decrypt_task_result(
            execution.result,
            rsa_private_key=user_rsa_private_key,
            ecdsa_public_key=server_ecdsa_public_key,
            metadata=execution.result_metadata,
        )
        assert decrypted == plaintext_state
