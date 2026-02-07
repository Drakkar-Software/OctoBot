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

from octobot_node.scheduler.task_context import encrypted_task
from tentacles.Services.Interfaces.node_api.models import Task
from tentacles.Services.Interfaces.node_api.enums import TaskResultKeys


class TestEncryptedTask:
    def test_encrypted_task_no_encryption_keys(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = None
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = None
        mock_settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY = None
        mock_settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY = None

        with mock.patch("octobot_node.scheduler.task_context.settings", mock_settings):
            task = Task(
                name="test_task",
                content="plain content",
                result=None
            )
            original_content = task.content

            with encrypted_task(task):
                # Content should remain unchanged
                assert task.content == original_content
                # Can modify task inside context
                task.result = {"status": "success"}

            # Content should still be unchanged after context
            assert task.content == original_content
            assert task.result == {"status": "success"}

    def test_encrypted_task_full_encryption_decryption(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = b"input_private_key"
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = b"input_public_key"
        mock_settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY = b"output_public_key"
        mock_settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY = b"output_private_key"

        task = Task(
            name="test_task",
            content="encrypted_content",
            content_metadata="input_metadata",
            result=None
        )
        original_content = task.content
        decrypted_content = "decrypted_content"
        encrypted_result = "encrypted_result"
        result_metadata = "result_metadata"

        mock_decrypt = mock.Mock(return_value=decrypted_content)
        mock_encrypt = mock.Mock(return_value=(encrypted_result, result_metadata))
        mock_json_dumps = mock.Mock(return_value='{"status": "success"}')

        with mock.patch("octobot_node.scheduler.task_context.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.task_context.decrypt_task_content", mock_decrypt), \
             mock.patch("octobot_node.scheduler.task_context.encrypt_task_result", mock_encrypt), \
             mock.patch("octobot_node.scheduler.task_context.json.dumps", mock_json_dumps):
            with encrypted_task(task):
                # Content should be decrypted
                assert task.content == decrypted_content
                # Set result inside context
                task.result = {"status": "success"}

            # Content should be restored
            assert task.content == original_content
            # Result should be encrypted
            assert task.result == encrypted_result
            assert task.result_metadata == result_metadata

    def test_encrypted_task_decryption_error(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = b"private_key"
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = b"public_key"
        mock_settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY = None
        mock_settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY = None

        task = Task(
            name="test_task",
            content="encrypted_content",
            content_metadata="metadata",
            result=None
        )
        original_content = task.content
        decryption_error = ValueError("Decryption failed")

        mock_decrypt = mock.Mock(side_effect=decryption_error)
        mock_logger = mock.Mock()

        with mock.patch("octobot_node.scheduler.task_context.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.task_context.decrypt_task_content", mock_decrypt), \
             mock.patch("octobot_node.scheduler.task_context.logger", mock_logger):
            with encrypted_task(task):
                # Content should remain unchanged on error
                assert task.content == original_content
                # Set a result
                task.result = {"status": "success"}

            # Content should still be original
            assert task.content == original_content
            # Result should be set to error format
            assert task.result[TaskResultKeys.STATUS.value] == "failed"
            assert task.result[TaskResultKeys.TASK.value] == {"name": "test_task"}
            assert task.result[TaskResultKeys.RESULT.value] == {}
            assert task.result[TaskResultKeys.ERROR.value] == str(decryption_error)
            mock_logger.error.assert_called_once()

    def test_encrypted_task_result_none(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = None
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = None
        mock_settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY = b"public_key"
        mock_settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY = b"private_key"

        task = Task(
            name="test_task",
            content="plain content",
            result=None
        )

        mock_encrypt = mock.Mock()

        with mock.patch("octobot_node.scheduler.task_context.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.task_context.encrypt_task_result", mock_encrypt):
            with encrypted_task(task):
                # Don't set result
                pass

            # Encryption should not be called when result is None
            mock_encrypt.assert_not_called()

    def test_encrypted_task_exception_during_context(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = b"private_key"
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = b"public_key"
        mock_settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY = None
        mock_settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY = None

        task = Task(
            name="test_task",
            content="encrypted_content",
            content_metadata="metadata"
        )
        original_content = task.content
        decrypted_content = "decrypted_content"

        mock_decrypt = mock.Mock(return_value=decrypted_content)

        with mock.patch("octobot_node.scheduler.task_context.settings", mock_settings), \
             mock.patch("octobot_node.scheduler.task_context.decrypt_task_content", mock_decrypt):
            # Exception should propagate, but content should be restored
            with pytest.raises(ValueError, match="Test exception"):
                with encrypted_task(task):
                    # Content should be decrypted
                    assert task.content == decrypted_content
                    # Raise exception
                    raise ValueError("Test exception")

            # Content should be restored even after exception
            assert task.content == original_content
