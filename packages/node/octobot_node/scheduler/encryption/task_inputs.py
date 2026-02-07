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

import json
import base64

from typing import Optional, Tuple
from octobot_node.config import settings
from octobot_node.scheduler.encryption import (
    ENCRYPTED_AES_KEY_B64_METADATA_KEY, 
    IV_B64_METADATA_KEY, 
    SIGNATURE_B64_METADATA_KEY, 
    MissingMetadataError, 
    EncryptionTaskError, 
    MetadataParsingError, 
    SignatureVerificationError
)
import octobot_commons.cryptography as cryptography

def decrypt_task_content(content: str, metadata: Optional[str] = None) -> str:
    if metadata is None:
        raise MissingMetadataError("No metadata provided for content decryption")

    try:
        metadata = json.loads(base64.b64decode(metadata).decode('utf-8'))
        encrypted_aes_key_b64 = metadata.get(ENCRYPTED_AES_KEY_B64_METADATA_KEY, None)
        iv_b64 = metadata.get(IV_B64_METADATA_KEY, None)
        signature_b64 = metadata.get(SIGNATURE_B64_METADATA_KEY, None)
    except Exception as e:
        raise MetadataParsingError(f"Failed to parse encrypted AES key or IV from metadata: {e}")

    if not encrypted_aes_key_b64 or not iv_b64 or not signature_b64:
        raise MissingMetadataError("No encrypted AES key or IV or signature provided for content decryption")

    try:
        content_bytes = base64.b64decode(content)
        encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
        iv = base64.b64decode(iv_b64)
        signature = base64.b64decode(signature_b64)
    except Exception as e:
        raise MetadataParsingError(f"Failed to decode base64-encoded data: {e}")

    data_to_verify = content_bytes + encrypted_aes_key + iv
    if not cryptography.verify_signature(data_to_verify, settings.TASKS_INPUTS_ECDSA_PUBLIC_KEY, signature):
        raise SignatureVerificationError("Signature verification failed")

    decrypted_aes_key = cryptography.rsa_decrypt_aes_key(encrypted_aes_key, settings.TASKS_INPUTS_RSA_PRIVATE_KEY)
    if not decrypted_aes_key:
        raise EncryptionTaskError("Failed to decrypt AES key")

    decrypted_content = cryptography.aes_gcm_decrypt(content_bytes, decrypted_aes_key, iv)
    if not decrypted_content:
        raise EncryptionTaskError("Failed to decrypt content")

    return decrypted_content.decode('utf-8')


def encrypt_task_content(content: str) -> Tuple[str, str]:
    aes_encryption_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()

    encrypted_content = cryptography.aes_gcm_encrypt(content.encode('utf-8'), aes_encryption_key, iv)
    if not encrypted_content:
        raise EncryptionTaskError("Failed to encrypt content")

    encrypted_aes_key = cryptography.rsa_encrypt_aes_key(aes_encryption_key, settings.TASKS_INPUTS_RSA_PUBLIC_KEY)
    if not encrypted_aes_key:
        raise EncryptionTaskError("Failed to encrypt AES key")

    data_to_sign = encrypted_content + encrypted_aes_key + iv
    signature = cryptography.sign_data(data_to_sign, settings.TASKS_INPUTS_ECDSA_PRIVATE_KEY)
    if not signature:
        raise EncryptionTaskError("Failed to sign data")

    metadata = {
        ENCRYPTED_AES_KEY_B64_METADATA_KEY: base64.b64encode(encrypted_aes_key).decode('utf-8'),
        IV_B64_METADATA_KEY: base64.b64encode(iv).decode('utf-8'),
        SIGNATURE_B64_METADATA_KEY: base64.b64encode(signature).decode('utf-8'),
    }
    encrypted_content_b64 = base64.b64encode(encrypted_content).decode('utf-8')
    metadata_json = json.dumps(metadata)
    metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('utf-8')
    return encrypted_content_b64, metadata_b64
