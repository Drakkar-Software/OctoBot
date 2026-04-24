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

import pytest
import mock

import octobot_node.scheduler.octobot_flow_client as octobot_flow_client
from octobot_node.scheduler.task_context import encrypted_task
from octobot_node.models import Task


class TestEncryptedTask:
    def test_encrypted_task_no_encryption_keys(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_SERVER_RSA_PRIVATE_KEY = None
        mock_settings.TASKS_USER_ECDSA_PUBLIC_KEY = None

        with mock.patch("octobot_node.config.settings", mock_settings):
            task = Task(
                name="test_task",
                content="plain content",
            )
            original_content = task.content

            with encrypted_task(task):
                # Content should remain unchanged
                assert task.content == original_content

            # Content should still be unchanged after context
            assert task.content == original_content

    def test_encrypted_task_decryption_error(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_SERVER_RSA_PRIVATE_KEY = b"private_key"
        mock_settings.TASKS_USER_ECDSA_PUBLIC_KEY = b"public_key"

        task = Task(
            name="test_task",
            content="encrypted_content",
            content_metadata="metadata",
        )
        original_content = task.content

        mock_decrypt = mock.Mock(side_effect=ValueError("Decryption failed"))
        mock_logger = mock.Mock()

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.encryption.decrypt_task_content", mock_decrypt), \
             mock.patch("octobot_node.scheduler.task_context.logger", mock_logger):
            with encrypted_task(task):
                # Content should remain unchanged on error
                assert task.content == original_content

            # Content should still be original
            assert task.content == original_content
            mock_logger.error.assert_called_once()

    def test_encrypted_task_exception_during_context(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_SERVER_RSA_PRIVATE_KEY = b"private_key"
        mock_settings.TASKS_USER_ECDSA_PUBLIC_KEY = b"public_key"

        task = Task(
            name="test_task",
            content="encrypted_content",
            content_metadata="metadata"
        )
        original_content = task.content
        decrypted_content = "decrypted_content"

        mock_decrypt = mock.Mock(return_value=decrypted_content)

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.encryption.decrypt_task_content", mock_decrypt):
            # Exception should propagate, but content should be restored
            with pytest.raises(ValueError, match="Test exception"):
                with encrypted_task(task):
                    # Content should be decrypted
                    assert task.content == decrypted_content
                    # Raise exception
                    raise ValueError("Test exception")

            # Content should be restored even after exception
            assert task.content == original_content

    def test_encrypted_task_to_update_result_with_description_encrypts_and_clears(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_SERVER_RSA_PRIVATE_KEY = None
        mock_settings.TASKS_USER_ECDSA_PUBLIC_KEY = None

        job_description = octobot_flow_client.OctoBotActionsJobDescription(
            state={}, auth_details={}, params={}
        )
        processed_action = mock.Mock()
        actions_dag = mock.Mock()
        to_update_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[processed_action],
            next_actions_description=job_description,
            actions_dag=actions_dag,
        )
        mock_encrypt = mock.Mock(return_value=("encrypted_payload", "encryption_meta"))

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch(
                 "octobot_node.scheduler.task_context.encryption.get_next_encrypted_if_needed_content_and_metadata",
                 mock_encrypt,
             ):
            task = Task(name="test_task", content="plain")
            with encrypted_task(task, to_update_result=to_update_result):
                pass

        mock_encrypt.assert_called_once_with(
            job_description.to_dict(include_default_values=False)
        )
        assert to_update_result.maybe_encrypted_next_actions_description == "encrypted_payload"
        assert to_update_result.next_actions_description_encryption_metadata == "encryption_meta"
        assert to_update_result.next_actions_description is None
        assert to_update_result.processed_actions == []
        assert to_update_result.actions_dag is None

    def test_encrypted_task_to_update_result_without_description_clears_sensitive_fields(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_SERVER_RSA_PRIVATE_KEY = None
        mock_settings.TASKS_USER_ECDSA_PUBLIC_KEY = None

        processed_action = mock.Mock()
        actions_dag = mock.Mock()
        to_update_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[processed_action],
            next_actions_description=None,
            actions_dag=actions_dag,
        )
        mock_encrypt = mock.Mock()

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch(
                 "octobot_node.scheduler.task_context.encryption.get_next_encrypted_if_needed_content_and_metadata",
                 mock_encrypt,
             ):
            task = Task(name="test_task", content="plain")
            with encrypted_task(task, to_update_result=to_update_result):
                pass

        mock_encrypt.assert_not_called()
        assert to_update_result.maybe_encrypted_next_actions_description is None
        assert to_update_result.next_actions_description_encryption_metadata is None
        assert to_update_result.next_actions_description is None
        assert to_update_result.processed_actions == []
        assert to_update_result.actions_dag is None

    def test_encrypted_task_to_update_result_runs_finally_after_exception(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_SERVER_RSA_PRIVATE_KEY = None
        mock_settings.TASKS_USER_ECDSA_PUBLIC_KEY = None

        job_description = octobot_flow_client.OctoBotActionsJobDescription(
            state={}, auth_details={}, params={}
        )
        to_update_result = octobot_flow_client.OctoBotActionsJobResult(
            processed_actions=[mock.Mock()],
            next_actions_description=job_description,
            actions_dag=mock.Mock(),
        )
        mock_encrypt = mock.Mock(return_value=("enc", "meta"))

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch(
                 "octobot_node.scheduler.task_context.encryption.get_next_encrypted_if_needed_content_and_metadata",
                 mock_encrypt,
             ):
            task = Task(name="test_task", content="plain")
            with pytest.raises(RuntimeError, match="inner"):
                with encrypted_task(task, to_update_result=to_update_result):
                    raise RuntimeError("inner")

        assert to_update_result.maybe_encrypted_next_actions_description == "enc"
        assert to_update_result.next_actions_description_encryption_metadata == "meta"
        assert to_update_result.processed_actions == []

    def test_encrypted_task_per_task_ecdsa_key_takes_precedence(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_SERVER_RSA_PRIVATE_KEY = b"server_rsa_priv"
        mock_settings.TASKS_USER_ECDSA_PUBLIC_KEY = b"env_global_key"

        task = Task(
            name="test_task",
            content="encrypted_content",
            content_metadata="metadata",
            user_ecdsa_public_key="per_task_key",
        )
        mock_decrypt = mock.Mock(return_value="decrypted_content")

        with mock.patch("octobot_node.config.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.encryption.decrypt_task_content", mock_decrypt):
            with encrypted_task(task):
                assert task.content == "decrypted_content"

        mock_decrypt.assert_called_once_with(
            "encrypted_content", "metadata", user_ecdsa_public_key=b"per_task_key"
        )
