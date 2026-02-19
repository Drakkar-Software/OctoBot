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
import json

import octobot_node.config
import octobot_node.models
import octobot_node.enums
import octobot_node.scheduler.encryption as encryption

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def encrypted_task(task: octobot_node.models.Task):
    """
    Context manager for automatically decrypting task content and encrypting task results.
    It first decrypts task.content if TASKS_INPUTS_RSA_PRIVATE_KEY is provided.
    Then it encrypts the result and restores original content on exit if TASKS_OUTPUTS_RSA_PUBLIC_KEY is provided
    """
    original_content = task.content
    decryption_error: Exception | None = None
    
    try:
        # Decrypt content if encryption keys are configured
        if octobot_node.config.settings.TASKS_INPUTS_RSA_PRIVATE_KEY and octobot_node.config.settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY:
            try:
                if not task.content_metadata:
                    raise encryption.MissingMetadataError("No metadata provided for content decryption")
                decrypted_content = encryption.decrypt_task_content(task.content, task.content_metadata)
                task.content = decrypted_content
            except Exception as e:
                logger.error(f"Failed to decrypt content: {e}")
                decryption_error = e
        
        yield task
    finally:
        # Restore original content if it was modified
        if task.content != original_content:
            task.content = original_content

        if task.result is not None:
            if decryption_error:
                task.result = {
                    octobot_node.enums.TaskResultKeys.STATUS.value: "failed", 
                    octobot_node.enums.TaskResultKeys.TASK.value: {"name": task.name}, 
                    octobot_node.enums.TaskResultKeys.RESULT.value: {}, 
                    octobot_node.enums.TaskResultKeys.ERROR.value: str(decryption_error)
                }

            # Encrypt result if encryption keys are configured
            if octobot_node.config.settings.TASKS_OUTPUTS_RSA_PUBLIC_KEY and octobot_node.config.settings.TASKS_OUTPUTS_ECDSA_PRIVATE_KEY:
                try:
                    result_json = json.dumps(task.result)
                    encrypted_result, metadata = encryption.encrypt_task_result(result_json)
                    task.result = encrypted_result
                    task.result_metadata = metadata
                except Exception as e:
                    logger.error(f"Failed to encrypt result: {e}")
                    # TODO: Handle encryption failure
