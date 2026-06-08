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
import datetime
import mock
import pytest
import dbos

import octobot_commons.cryptography
import octobot_protocol.models as protocol_models
import octobot_node.config
import octobot_node.models
import octobot_node.scheduler.encryption as encryption
import octobot_node.scheduler.encryption.task_inputs as task_inputs_encryption
import octobot_node.scheduler.workflows.params as params
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.scheduler.scheduler as scheduler_module

PARENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
CHILD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa-iter-1"


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


def _build_mock_workflow_status_no_output(task: octobot_node.models.Task, workflow_id: str = PARENT_ID) -> mock.Mock:
    inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
    ws = mock.Mock(spec=dbos.WorkflowStatus)
    ws.workflow_id = workflow_id
    ws.name = "test-task"
    ws.status = dbos.WorkflowStatusString.SUCCESS.value
    ws.output = None
    ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
    ws.created_at = None
    ws.updated_at = 1
    return ws


def _build_mock_workflow_status_error(task: octobot_node.models.Task, error, workflow_id: str = PARENT_ID) -> mock.Mock:
    inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
    ws = mock.Mock(spec=dbos.WorkflowStatus)
    ws.workflow_id = workflow_id
    ws.name = "test-task"
    ws.status = dbos.WorkflowStatusString.ERROR.value
    ws.output = None
    ws.error = error
    ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
    ws.created_at = None
    ws.updated_at = 2
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
    async def test_get_results_returns_empty_result_no_crypto(self):
        """get_results must return result='' and result_metadata='' — no crypto on list path."""
        task = octobot_node.models.Task(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            name="test-task",
            content="encrypted_content",
            content_metadata="meta",
            type="execute_actions",
        )
        ws = _build_mock_workflow_status(task, "encrypted_state", "state_meta")

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        with mock.patch("octobot_node.scheduler.encryption.encrypt_task_result") as mock_crypto:
            executions = await sched.get_results()

        assert len(executions) == 1
        assert executions[0].result == ""
        assert executions[0].result_metadata == ""
        mock_crypto.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_results_sets_is_encrypted_from_content_metadata(self):
        """Execution.is_encrypted reflects whether the task input was encrypted."""
        encrypted_task = octobot_node.models.Task(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            name="encrypted-task",
            content="cipher",
            content_metadata="iv-blob",
            type="execute_actions",
        )
        plain_task = octobot_node.models.Task(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            name="plain-task",
            content="raw-content",
            content_metadata=None,
            type="execute_actions",
        )
        ws_enc = _build_mock_workflow_status(encrypted_task, None, None, workflow_id=encrypted_task.id)
        ws_plain = _build_mock_workflow_status(plain_task, None, None, workflow_id=plain_task.id)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws_enc, ws_plain])

        executions = await sched.get_results()

        assert len(executions) == 2
        by_id = {e.id: e for e in executions}
        assert by_id[encrypted_task.id].is_encrypted is True
        assert by_id[plain_task.id].is_encrypted is False

    @pytest.mark.asyncio
    async def test_get_results_dbos_error_workflow_sets_error(self):
        """DBOS ERROR workflow (Python exception) must have error set so UI classifies it as errored."""
        task = octobot_node.models.Task(
            id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            name="failed-task",
            content=None,
            type="execute_actions",
        )
        inputs = params.AutomationWorkflowInputs(task=task)
        ws = mock.Mock(spec=dbos.WorkflowStatus)
        ws.workflow_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        ws.name = "failed-task"
        ws.status = dbos.WorkflowStatusString.ERROR.value
        ws.output = None
        ws.error = RuntimeError("Connection timeout")
        ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
        ws.created_at = None
        ws.updated_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        executions = await sched.get_results()

        assert len(executions) == 1
        execution = executions[0]
        assert execution.error  # must be truthy for UI to show as "errored"
        assert "Connection timeout" in execution.error
        assert execution.result == ""

    @pytest.mark.asyncio
    async def test_get_results_dbos_error_no_exception_fallback(self):
        """DBOS ERROR workflow with no exception object still sets a non-empty error."""
        task = octobot_node.models.Task(
            id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            name="failed-task",
            content=None,
            type="execute_actions",
        )
        inputs = params.AutomationWorkflowInputs(task=task)
        ws = mock.Mock(spec=dbos.WorkflowStatus)
        ws.workflow_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
        ws.name = "failed-task"
        ws.status = dbos.WorkflowStatusString.ERROR.value
        ws.output = None
        ws.error = None
        ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
        ws.created_at = None
        ws.updated_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        executions = await sched.get_results()

        assert len(executions) == 1
        assert executions[0].error  # fallback string must be truthy

    @pytest.mark.asyncio
    async def test_get_results_success_with_output_error_marks_failed(self):
        """DBOS SUCCESS workflow whose output.error is set must surface as FAILED."""
        task = octobot_node.models.Task(
            id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            name="business-failed-task",
            content=None,
            type="execute_actions",
        )
        output = params.AutomationWorkflowOutput(error="Trade rejected by exchange")
        inputs = params.AutomationWorkflowInputs(task=task)
        ws = mock.Mock(spec=dbos.WorkflowStatus)
        ws.workflow_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        ws.name = "business-failed-task"
        ws.status = dbos.WorkflowStatusString.SUCCESS.value
        ws.output = json.dumps(output.to_dict())
        ws.error = None
        ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
        ws.created_at = None
        ws.updated_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        executions = await sched.get_results()

        assert len(executions) == 1
        assert executions[0].status == octobot_node.models.TaskStatus.FAILED
        assert executions[0].error == "Trade rejected by exchange"

    @pytest.mark.asyncio
    async def test_get_results_success_with_malformed_output_falls_back_to_completed(self):
        """SUCCESS workflow with unparseable output JSON must NOT crash and must default to COMPLETED.

        Regression guard: a parse exception inside the SUCCESS branch must not bubble up
        and must not flip the task to FAILED — the workflow ran fine at DBOS level.
        """
        task = octobot_node.models.Task(
            id="ffffffff-ffff-ffff-ffff-ffffffffffff",
            name="malformed-output-task",
            content=None,
            type="execute_actions",
        )
        inputs = params.AutomationWorkflowInputs(task=task)
        ws = mock.Mock(spec=dbos.WorkflowStatus)
        ws.workflow_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        ws.name = "malformed-output-task"
        ws.status = dbos.WorkflowStatusString.SUCCESS.value
        ws.output = "{not valid json"
        ws.error = None
        ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
        ws.created_at = None
        ws.updated_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        executions = await sched.get_results()

        assert len(executions) == 1
        assert executions[0].status == octobot_node.models.TaskStatus.COMPLETED
        assert executions[0].error is None

    @pytest.mark.asyncio
    async def test_get_results_wallet_filter_keeps_legacy_task_without_wallet_address(self):
        """Regression: tasks created before the multi-wallet refactor have task.wallet_address=None.
        They must remain visible to any caller — never dropped by the wallet filter.
        """
        legacy_task = octobot_node.models.Task(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            name="legacy-task",
            content=None,
            type="execute_actions",
            wallet_address=None,  # pre-multi-tenant: no wallet attached
        )
        ws = _build_mock_workflow_status(legacy_task, None, None, workflow_id=legacy_task.id)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        executions = await sched.get_results(wallet_address="0xcaller")

        assert len(executions) == 1
        assert executions[0].id == legacy_task.id

    @pytest.mark.asyncio
    async def test_get_results_wallet_filter_keeps_workflow_with_unparseable_input(self):
        """Regression: a crashed workflow may have unparseable input → get_automation_input_task returns None.
        Must remain visible — silently dropping is what hid all errored tasks before.
        """
        ws = mock.Mock(spec=dbos.WorkflowStatus)
        ws.workflow_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        ws.name = "crashed-task"
        ws.status = dbos.WorkflowStatusString.ERROR.value
        ws.output = None
        ws.error = RuntimeError("crashed before input was persisted")
        ws.input = {"args": [], "kwargs": {}}  # nothing parseable
        ws.created_at = None
        ws.updated_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        executions = await sched.get_results(wallet_address="0xcaller")

        assert len(executions) == 1
        assert executions[0].status == octobot_node.models.TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_get_results_wallet_filter_drops_task_with_explicit_other_wallet(self):
        """Sanity check that the filter still drops tasks explicitly owned by a different wallet."""
        other_task = octobot_node.models.Task(
            id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            name="other-task",
            content=None,
            type="execute_actions",
            wallet_address="0xother",
        )
        ws = _build_mock_workflow_status(other_task, None, None, workflow_id=other_task.id)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        executions = await sched.get_results(wallet_address="0xcaller")

        assert executions == []


class TestGetWorkflowsExportResults:

    def _make_task(self, wallet_address: str = "wallet-a") -> octobot_node.models.Task:
        return octobot_node.models.Task(
            id=PARENT_ID,
            name="test-task",
            content="encrypted_content",
            content_metadata="meta",
            type="execute_actions",
            wallet_address=wallet_address,
        )

    @pytest.mark.asyncio
    async def test_picks_child_with_output_for_multi_iteration_parent(self):
        """For multi-iteration task: parent output=None, child has actual output → child is used."""
        task = self._make_task()
        parent_ws = _build_mock_workflow_status_no_output(task, workflow_id=PARENT_ID)
        child_output = params.AutomationWorkflowOutput(state="encrypted_state", state_metadata=None)
        child_ws = _build_mock_workflow_status(task, "encrypted_state", None, workflow_id=CHILD_ID)
        child_ws.updated_at = 10

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[parent_ws, child_ws])
        mock_instance.retrieve_workflow_async = mock.AsyncMock()

        def _fake_encrypted_task(result_task):
            result_task.content = "decrypted_plaintext"
            ctx = mock.MagicMock()
            ctx.__enter__ = mock.Mock(return_value=None)
            ctx.__exit__ = mock.Mock(return_value=False)
            return ctx

        with mock.patch.object(
            type(octobot_node.config.settings),
            "is_node_side_encryption_enabled",
            new_callable=mock.PropertyMock,
            return_value=True,
        ), mock.patch(
            "octobot_node.config.settings.TASKS_USER_RSA_PUBLIC_KEY", b"user-rsa-key"
        ), mock.patch(
            "octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY", b"server-ecdsa-key"
        ), mock.patch(
            "octobot_node.scheduler.task_context.encrypted_task",
            side_effect=_fake_encrypted_task,
        ), mock.patch(
            "octobot_node.scheduler.encryption.encrypt_task_result",
            return_value=("user_encrypted", "user_meta"),
        ) as mock_encrypt:
            result = await sched.get_workflows_export_results([PARENT_ID], None)

        assert result[PARENT_ID]["result"] == "user_encrypted"
        assert result[PARENT_ID]["result_metadata"] == "user_meta"
        mock_instance.retrieve_workflow_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_crypto_when_encryption_disabled(self):
        """When node-side encryption is off, state is returned as-is without crypto."""
        task = self._make_task()
        child_ws = _build_mock_workflow_status(task, "plain_state", None, workflow_id=CHILD_ID)
        child_ws.updated_at = 10
        parent_ws = _build_mock_workflow_status_no_output(task, workflow_id=PARENT_ID)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[parent_ws, child_ws])

        with mock.patch.object(
            type(octobot_node.config.settings),
            "is_node_side_encryption_enabled",
            new_callable=mock.PropertyMock,
            return_value=False,
        ), mock.patch(
            "octobot_node.scheduler.encryption.encrypt_task_result"
        ) as mock_encrypt:
            result = await sched.get_workflows_export_results([PARENT_ID], None)

        assert result[PARENT_ID] == {"result": "plain_state", "result_metadata": ""}
        mock_encrypt.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_workflow_has_output(self):
        """All workflows in group have output=None → returns empty result, no exception."""
        task = self._make_task()
        parent_ws = _build_mock_workflow_status_no_output(task, workflow_id=PARENT_ID)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[parent_ws])

        with mock.patch(
            "octobot_node.scheduler.encryption.encrypt_task_result"
        ) as mock_encrypt:
            result = await sched.get_workflows_export_results([PARENT_ID], None)

        assert result[PARENT_ID] == {"result": "", "result_metadata": ""}
        mock_encrypt.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_error_for_all_failed_group(self):
        """All workflows ERROR → error message surfaced in response."""
        task = self._make_task()
        error_ws = _build_mock_workflow_status_error(task, RuntimeError("boom"), workflow_id=PARENT_ID)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[error_ws])

        result = await sched.get_workflows_export_results([PARENT_ID], None)

        assert "error" in result[PARENT_ID]
        assert "boom" in result[PARENT_ID]["error"]

    @pytest.mark.asyncio
    async def test_rejects_other_wallet(self):
        """wallet_address filter: task belonging to a different wallet returns forbidden."""
        task = self._make_task(wallet_address="wallet-b")
        child_ws = _build_mock_workflow_status(task, "state", None, workflow_id=CHILD_ID)
        child_ws.updated_at = 10
        parent_ws = _build_mock_workflow_status_no_output(task, workflow_id=PARENT_ID)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[parent_ws, child_ws])

        with mock.patch(
            "octobot_node.scheduler.encryption.encrypt_task_result"
        ) as mock_encrypt:
            result = await sched.get_workflows_export_results([PARENT_ID], "wallet-a")

        assert result[PARENT_ID] == {"error": "forbidden"}
        mock_encrypt.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_call_retrieve_workflow_async(self):
        """New implementation must not call retrieve_workflow_async for any task."""
        task = self._make_task()
        child_ws = _build_mock_workflow_status(task, "state", None, workflow_id=CHILD_ID)
        child_ws.updated_at = 10

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[child_ws])
        mock_instance.retrieve_workflow_async = mock.AsyncMock()

        with mock.patch.object(
            type(octobot_node.config.settings),
            "is_node_side_encryption_enabled",
            new_callable=mock.PropertyMock,
            return_value=False,
        ):
            await sched.get_workflows_export_results([PARENT_ID], None)

        mock_instance.retrieve_workflow_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_found_when_task_id_missing(self):
        """task_id not in any workflow group → error: not found."""
        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[])

        result = await sched.get_workflows_export_results([PARENT_ID], None)

        assert result[PARENT_ID] == {"error": "not found"}

    @pytest.mark.asyncio
    async def test_encrypted_state_no_user_key_returns_decrypted_plaintext(self):
        """Regression: encrypted state + no user RSA key must return server-decrypted plaintext,
        not the raw server-side ciphertext."""
        task = self._make_task()
        child_ws = _build_mock_workflow_status(
            task, "server_encrypted_ciphertext", "some_state_metadata", workflow_id=CHILD_ID
        )
        child_ws.updated_at = 10
        parent_ws = _build_mock_workflow_status_no_output(task, workflow_id=PARENT_ID)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[parent_ws, child_ws])

        def _fake_encrypted_task(result_task):
            result_task.content = "decrypted_plaintext"
            ctx = mock.MagicMock()
            ctx.__enter__ = mock.Mock(return_value=None)
            ctx.__exit__ = mock.Mock(return_value=False)
            return ctx

        with mock.patch.object(
            type(octobot_node.config.settings),
            "is_node_side_encryption_enabled",
            new_callable=mock.PropertyMock,
            return_value=True,
        ), mock.patch(
            "octobot_node.config.settings.TASKS_USER_RSA_PUBLIC_KEY", None
        ), mock.patch(
            "octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY", None
        ), mock.patch(
            "octobot_node.scheduler.task_context.encrypted_task",
            side_effect=_fake_encrypted_task,
        ), mock.patch(
            "octobot_node.scheduler.encryption.encrypt_task_result"
        ) as mock_encrypt:
            result = await sched.get_workflows_export_results([PARENT_ID], None)

        assert result[PARENT_ID] == {"result": "decrypted_plaintext", "result_metadata": ""}
        assert result[PARENT_ID]["result"] != "server_encrypted_ciphertext"
        mock_encrypt.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_key_encrypts_plaintext_imported_task(self):
        """Request-supplied user_rsa_public_key causes result encryption even for plaintext-imported tasks."""
        task = self._make_task()
        child_ws = _build_mock_workflow_status(task, "plain_state", None, workflow_id=CHILD_ID)
        child_ws.updated_at = 10
        parent_ws = _build_mock_workflow_status_no_output(task, workflow_id=PARENT_ID)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[parent_ws, child_ws])

        user_key_pem = "-----BEGIN PUBLIC KEY-----\nfakekey\n-----END PUBLIC KEY-----"

        with mock.patch(
            "octobot_node.config.settings.TASKS_SERVER_ECDSA_PRIVATE_KEY", b"ecdsa-key"
        ), mock.patch(
            "octobot_node.config.settings.TASKS_USER_RSA_PUBLIC_KEY", None
        ), mock.patch(
            "octobot_node.scheduler.encryption.encrypt_task_result",
            return_value=("user_encrypted", "user_meta"),
        ) as mock_encrypt:
            result = await sched.get_workflows_export_results(
                [PARENT_ID], None, user_rsa_public_key=user_key_pem
            )

        assert result[PARENT_ID] == {"result": "user_encrypted", "result_metadata": "user_meta"}
        mock_encrypt.assert_called_once()
        call_kwargs = mock_encrypt.call_args
        assert call_kwargs[1]["rsa_public_key"] == user_key_pem.encode("utf-8")


class TestSchedulerGetPendingTasks:

    def _make_pending_ws(self, task: octobot_node.models.Task, workflow_name: str = "execute_automation") -> mock.Mock:
        inputs = params.AutomationWorkflowInputs(task=task, execution_time=0)
        ws = mock.Mock(spec=dbos.WorkflowStatus)
        ws.workflow_id = task.id
        ws.name = workflow_name
        ws.status = dbos.WorkflowStatusString.ENQUEUED.value
        ws.output = None
        ws.error = None
        ws.input = {"args": [inputs.to_dict()], "kwargs": {}}
        ws.created_at = None
        ws.updated_at = None
        return ws

    @pytest.mark.asyncio
    async def test_get_pending_tasks_uses_task_name_not_workflow_name(self):
        """Pending execution.name must come from task input, not DBOS workflow_status.name."""
        task = octobot_node.models.Task(
            id="11111111-1111-1111-1111-111111111111",
            name="Real trade 1",
            content=None,
            type="execute_actions",
        )
        ws = self._make_pending_ws(task, workflow_name="execute_automation")

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        with mock.patch("octobot_node.scheduler.workflows_util.get_automation_state_reader", return_value=None):
            executions = await sched.get_pending_tasks()

        assert len(executions) == 1
        assert executions[0].name == "Real trade 1"

    @pytest.mark.asyncio
    async def test_get_pending_tasks_preserves_none_name_when_task_has_no_name(self):
        """When task.name is None, execution.name stays None (task input wins; DBOS name is never substituted)."""
        task = octobot_node.models.Task(
            id="22222222-2222-2222-2222-222222222222",
            name=None,
            content=None,
            type="execute_actions",
        )
        ws = self._make_pending_ws(task, workflow_name="execute_automation")

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[ws])

        with mock.patch("octobot_node.scheduler.workflows_util.get_automation_state_reader", return_value=None):
            executions = await sched.get_pending_tasks()

        assert len(executions) == 1
        assert executions[0].name is None


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


class TestSchedulerGetAutomationStates:

    @pytest.mark.asyncio
    async def test_error_workflow_reports_failed_not_running(self):
        """DBOS ERROR with input-only task content must not surface as running in protocol state."""
        task = octobot_node.models.Task(
            id=PARENT_ID,
            name="failed-automation",
            content=_running_automation_task_content(),
            type="execute_actions",
        )
        error_ws = _build_mock_workflow_status_error(task, RuntimeError("DBOSUnexpectedStepError"), workflow_id=PARENT_ID)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[error_ws])

        automation_states = await sched.get_automation_states(None)

        assert len(automation_states) == 1
        assert automation_states[0].id == PARENT_ID
        assert automation_states[0].status == protocol_models.WorkflowStatus.FAILED
        assert "DBOSUnexpectedStepError" in (automation_states[0].error or "")
        assert automation_states[0].error_message is None

    @pytest.mark.asyncio
    async def test_success_workflow_with_output_preserves_metadata_name(self):
        """Completed automation with workflow output must keep task.name in protocol metadata."""
        task = octobot_node.models.Task(
            id=PARENT_ID,
            name="my-automation",
            content=_running_automation_task_content(),
            type="execute_actions",
        )
        success_ws = _build_mock_workflow_status(
            task,
            encrypted_state=_running_automation_task_content(),
            state_metadata="",
            workflow_id=PARENT_ID,
        )

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(return_value=[success_ws])

        automation_states = await sched.get_automation_states(None)

        assert len(automation_states) == 1
        assert automation_states[0].id == PARENT_ID
        assert automation_states[0].metadata.name == "my-automation"


class TestSchedulerListUserActions:
    @pytest.mark.asyncio
    async def test_returns_empty_when_instance_missing(self):
        sched = scheduler_module.Scheduler()
        sched.INSTANCE = None
        assert await sched.list_user_actions("0xabc") == []

    @pytest.mark.asyncio
    async def test_merges_active_input_and_terminal_output_sorted_by_created_at(self):
        wallet_segment = "0xw1"
        ua_pending = protocol_models.UserAction(
            id="ua-p",
            configuration=None,
            created_at=datetime.datetime(2024, 6, 1, tzinfo=datetime.UTC),
        )
        inputs_pending = params.UserActionWorkflowInputs(
            wallet_address=wallet_segment,
            user_action=ua_pending,
        ).to_dict(include_default_values=False)
        workflow_pending = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_pending.workflow_id = "wf-pending-1"
        workflow_pending.input = {"args": [inputs_pending], "kwargs": {}}
        workflow_pending.created_at = datetime.datetime(2024, 6, 2, tzinfo=datetime.UTC)

        ua_done = protocol_models.UserAction(
            id="ua-done",
            status=protocol_models.UserActionStatus.COMPLETED,
            configuration=None,
            created_at=datetime.datetime(2024, 5, 1, tzinfo=datetime.UTC),
        )
        output_payload = params.UserActionWorkflowOutput(
            wallet_address=wallet_segment,
            updated_user_action=ua_done,
        ).to_dict(include_default_values=False)
        workflow_done = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_done.workflow_id = "wf-done-1"
        workflow_done.input = {"args": [], "kwargs": {}}
        workflow_done.output = output_payload
        workflow_done.created_at = datetime.datetime(2024, 5, 2, tzinfo=datetime.UTC)

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(
            side_effect=[[workflow_pending], [workflow_done]],
        )
        listed = await sched.list_user_actions(wallet_segment)
        assert [user_action_row.id for user_action_row in listed] == ["ua-done", "ua-p"]

    @pytest.mark.asyncio
    async def test_wallet_filter_excludes_other_wallet_pending_rows(self):
        wallet_a = "0xw_a"
        wallet_b = "0xw_b"
        ua_a = protocol_models.UserAction(id="ua-a", configuration=None)
        ua_b = protocol_models.UserAction(id="ua-b", configuration=None)
        inp_a = params.UserActionWorkflowInputs(wallet_address=wallet_a, user_action=ua_a).to_dict(
            include_default_values=False,
        )
        inp_b = params.UserActionWorkflowInputs(wallet_address=wallet_b, user_action=ua_b).to_dict(
            include_default_values=False,
        )
        workflow_a = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_a.workflow_id = "wfa"
        workflow_a.input = {"args": [inp_a], "kwargs": {}}
        workflow_a.created_at = None
        workflow_b = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_b.workflow_id = "wfb"
        workflow_b.input = {"args": [inp_b], "kwargs": {}}
        workflow_b.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[workflow_a, workflow_b], []])
        listed = await sched.list_user_actions(wallet_a)
        assert len(listed) == 1
        assert listed[0].id == "ua-a"

    @pytest.mark.asyncio
    async def test_terminal_without_output_builds_failed_action_from_input(self):
        wallet_segment = "0xw_fail"
        ua_in = protocol_models.UserAction(id="ua-fail", configuration=None)
        inp = params.UserActionWorkflowInputs(
            wallet_address=wallet_segment,
            user_action=ua_in,
        ).to_dict(include_default_values=False)
        workflow_error = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_error.workflow_id = "wf-err"
        workflow_error.input = {"args": [inp], "kwargs": {}}
        workflow_error.output = None
        workflow_error.error = "dbos boom"
        workflow_error.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[], [workflow_error]])
        listed = await sched.list_user_actions(wallet_segment)
        assert len(listed) == 1
        assert listed[0].status == protocol_models.UserActionStatus.FAILED
        inner = listed[0].result.actual_instance
        assert isinstance(inner, protocol_models.AccountActionResult)
        assert inner.error_details is not None
        assert "dbos boom" in inner.error_details

    @pytest.mark.asyncio
    async def test_terminal_without_output_uses_exchange_config_result_for_exchange_config_action(self):
        wallet_segment = "0xw_exchange_config_fail"
        configuration_inner = protocol_models.CreateExchangeConfigConfiguration(
            action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
            configuration=protocol_models.ExchangeConfig(
                id="cfg-fail",
                name="binance-main",
                exchange="binanceus",
                sandboxed=False,
            ),
        )
        ua_in = protocol_models.UserAction(
            id="ua-exchange-config-fail",
            configuration=protocol_models.UserActionConfiguration.from_json(configuration_inner.to_json()),
        )
        inp = params.UserActionWorkflowInputs(
            wallet_address=wallet_segment,
            user_action=ua_in,
        ).to_dict(include_default_values=False)
        workflow_error = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_error.workflow_id = "wf-exchange-config-err"
        workflow_error.input = {"args": [inp], "kwargs": {}}
        workflow_error.output = None
        workflow_error.error = "exchange config boom"
        workflow_error.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[], [workflow_error]])
        listed = await sched.list_user_actions(wallet_segment)
        assert len(listed) == 1
        assert listed[0].status == protocol_models.UserActionStatus.FAILED
        inner = listed[0].result.actual_instance
        assert isinstance(inner, protocol_models.ExchangeConfigActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.EXCHANGE_CONFIG
        assert inner.error_message == protocol_models.ExchangeConfigActionResultErrorMessage.INTERNAL_ERROR
        assert inner.error_details is not None
        assert "exchange config boom" in inner.error_details

    @pytest.mark.asyncio
    async def test_terminal_without_output_uses_automation_result_for_automation_action(self):
        wallet_segment = "0xw_automation_fail"
        configuration_inner = protocol_models.StopAutomationConfiguration(
            id="auto-stop-fail",
            action_type=protocol_models.UserActionType.AUTOMATION_STOP,
        )
        ua_in = protocol_models.UserAction(
            id="ua-automation-fail",
            configuration=protocol_models.UserActionConfiguration.from_json(configuration_inner.to_json()),
        )
        inp = params.UserActionWorkflowInputs(
            wallet_address=wallet_segment,
            user_action=ua_in,
        ).to_dict(include_default_values=False)
        workflow_error = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_error.workflow_id = "wf-automation-err"
        workflow_error.input = {"args": [inp], "kwargs": {}}
        workflow_error.output = None
        workflow_error.error = "automation boom"
        workflow_error.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[], [workflow_error]])
        listed = await sched.list_user_actions(wallet_segment)
        assert len(listed) == 1
        assert listed[0].status == protocol_models.UserActionStatus.FAILED
        inner = listed[0].result.actual_instance
        assert isinstance(inner, protocol_models.AutomationActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.AUTOMATION
        assert inner.error_message == protocol_models.AutomationActionResultErrorMessage.INTERNAL_ERROR
        assert inner.error_details is not None
        assert "automation boom" in inner.error_details

    @pytest.mark.asyncio
    async def test_list_user_actions_uses_explicit_non_terminal_and_terminal_status_partitions(self):
        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[], []])
        await sched.list_user_actions("0xwallet", active_only=False)
        assert mock_instance.list_workflows_async.await_count == 2
        input_status_values = set(mock_instance.list_workflows_async.await_args_list[0].kwargs["status"])
        terminal_status_values = set(mock_instance.list_workflows_async.await_args_list[1].kwargs["status"])
        expected_input_status_values = {
            status.value for status in workflows_util.get_user_action_input_workflow_statuses()
        }
        expected_terminal_status_values = {
            status.value for status in workflows_util.get_user_action_terminal_workflow_statuses()
        }
        assert input_status_values == expected_input_status_values
        assert terminal_status_values == expected_terminal_status_values
        assert "SUCCESS" not in input_status_values

    @pytest.mark.asyncio
    async def test_active_only_false_terminal_unparseable_appears_once(self):
        wallet_segment = "0xw_debug"
        workflow_terminal = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_terminal.workflow_id = "wf-terminal-unparseable"
        workflow_terminal.input = {"args": [], "kwargs": {}}
        workflow_terminal.output = None
        workflow_terminal.error = "workflow crashed"
        workflow_terminal.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[], [workflow_terminal]])
        listed = await sched.list_user_actions(wallet_segment, active_only=False)
        assert len(listed) == 1
        assert listed[0].id == "wf-terminal-unparseable"
        assert listed[0].status == protocol_models.UserActionStatus.FAILED

    @pytest.mark.asyncio
    async def test_delayed_workflow_with_empty_input_returns_minimal_pending_action(self):
        wallet_segment = "0xw_delayed"
        workflow_delayed = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_delayed.workflow_id = "wf-delayed-unparseable"
        workflow_delayed.status = dbos.WorkflowStatusString.DELAYED.value
        workflow_delayed.input = {"args": [], "kwargs": {}}
        workflow_delayed.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[workflow_delayed], []])
        listed = await sched.list_user_actions(wallet_segment)
        assert len(listed) == 1
        assert listed[0].id == "wf-delayed-unparseable"
        assert listed[0].status == protocol_models.UserActionStatus.PENDING

    @pytest.mark.asyncio
    async def test_active_workflow_with_empty_input_returns_minimal_pending_action(self):
        wallet_segment = "0xw_active_empty"
        workflow_enqueued = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_enqueued.workflow_id = "wf-enqueued-empty"
        workflow_enqueued.input = {"args": [], "kwargs": {}}
        workflow_enqueued.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[workflow_enqueued], []])
        listed = await sched.list_user_actions(wallet_segment)
        assert len(listed) == 1
        assert listed[0].id == "wf-enqueued-empty"
        assert listed[0].status == protocol_models.UserActionStatus.PENDING

    @pytest.mark.asyncio
    async def test_terminal_workflow_with_empty_input_returns_minimal_failed_action(self):
        wallet_segment = "0xw_terminal_empty"
        workflow_error = mock.Mock(spec=dbos.WorkflowStatus)
        workflow_error.workflow_id = "wf-terminal-empty"
        workflow_error.input = {"args": [], "kwargs": {}}
        workflow_error.output = None
        workflow_error.error = "persist failed"
        workflow_error.created_at = None

        sched, mock_instance = _make_scheduler_with_mock_instance()
        mock_instance.list_workflows_async = mock.AsyncMock(side_effect=[[], [workflow_error]])
        listed = await sched.list_user_actions(wallet_segment)
        assert len(listed) == 1
        assert listed[0].id == "wf-terminal-empty"
        assert listed[0].status == protocol_models.UserActionStatus.FAILED
        inner = listed[0].result.actual_instance
        assert isinstance(inner, protocol_models.AccountActionResult)
        assert inner.error_details is not None
        assert "persist failed" in inner.error_details
