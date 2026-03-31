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
from octobot_node.models import Task


class TestEncryptedTask:
    def test_encrypted_task_no_encryption_keys(self) -> None:
        mock_settings = mock.Mock()
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = None
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = None

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
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = b"private_key"
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = b"public_key"

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
        mock_settings.TASKS_INPUTS_RSA_PRIVATE_KEY = b"private_key"
        mock_settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY = b"public_key"

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
