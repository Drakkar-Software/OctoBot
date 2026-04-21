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
import typing

import octobot_node.config
import octobot_node.models
import octobot_node.scheduler.encryption as encryption
import octobot_node.scheduler.octobot_flow_client

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def encrypted_task(
    task: octobot_node.models.Task,
    to_update_result: typing.Optional["octobot_node.scheduler.octobot_flow_client.OctoBotActionsJobResult"] = None
):
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

        if to_update_result is not None:
            # ensure maybe_encrypted_next_actions_description is encrypted if needed
            if isinstance(
                to_update_result.next_actions_description,
                octobot_node.scheduler.octobot_flow_client.OctoBotActionsJobDescription
            ):
                maybe_encrypted_next_actions_description, next_actions_description_encryption_metadata = encryption.get_next_encrypted_if_needed_content_and_metadata(
                    to_update_result.next_actions_description.to_dict(include_default_values=False)
                )
            else:
                maybe_encrypted_next_actions_description = None
                next_actions_description_encryption_metadata = None
            # store potentially encrypted data
            to_update_result.maybe_encrypted_next_actions_description = maybe_encrypted_next_actions_description
            to_update_result.next_actions_description_encryption_metadata = next_actions_description_encryption_metadata
            # clear potentially sensitive data
            to_update_result.next_actions_description = None
            to_update_result.processed_actions.clear()
            to_update_result.actions_dag = None
