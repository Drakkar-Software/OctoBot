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

# Encryption tasks constants
ENCRYPTED_AES_KEY_B64_METADATA_KEY = "ENCRYPTED_AES_KEY_B64"
IV_B64_METADATA_KEY = "IV_B64"
SIGNATURE_B64_METADATA_KEY = "SIGNATURE_B64"

# Encryption tasks errors
class MissingMetadataError(Exception):
    pass

class MetadataParsingError(Exception):
    pass

class EncryptionTaskError(Exception):
    pass

class SignatureVerificationError(Exception):
    pass

from octobot_node.scheduler.encryption import task_inputs
from octobot_node.scheduler.encryption.task_inputs import (decrypt_task_content, encrypt_task_content)

from octobot_node.scheduler.encryption import task_outputs
from octobot_node.scheduler.encryption.task_outputs import (encrypt_task_result, decrypt_task_result)

__all__ = [
    "ENCRYPTED_AES_KEY_B64_METADATA_KEY",
    "IV_B64_METADATA_KEY",
    "SIGNATURE_B64_METADATA_KEY",
    "MissingMetadataError",
    "MetadataParsingError",
    "EncryptionTaskError",
    "SignatureVerificationError",
    "decrypt_task_content",
    "encrypt_task_content",
    "encrypt_task_result",
    "decrypt_task_result"
]