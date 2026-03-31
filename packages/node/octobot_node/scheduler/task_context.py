#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import contextlib
import logging

import octobot_node.config
import octobot_node.models
import octobot_node.scheduler.encryption as encryption

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def encrypted_task(task: octobot_node.models.Task):
    """
    Context manager for automatically decrypting task content.
    Decrypts task.content if TASKS_INPUTS_RSA_PRIVATE_KEY is provided,
    and restores original content on exit.
    """
    original_content = task.content

    try:
        # Decrypt content if input encryption keys are configured
        settings = octobot_node.config.settings
        if (settings.TASKS_INPUTS_RSA_PRIVATE_KEY
                and settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY
                and task.content_metadata):
            try:
                decrypted_content = encryption.decrypt_task_content(task.content, task.content_metadata)
                task.content = decrypted_content
            except Exception as e:
                logger.error(f"Failed to decrypt content: {e}")

        yield task
    finally:
        # Restore original content if it was modified
        if task.content != original_content:
            task.content = original_content
