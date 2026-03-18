#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

import base64
import os
import secrets
import shutil
import time
import traceback
import uuid
from typing import Any

import octobot_commons.authentication as authentication
import octobot_commons.logging as logging

from starfish_sdk import StarfishClient, SyncManager

import octobot.constants

logger = logging.get_logger("ErrorSharing")

ERRORS_PUSH_PATH_TEMPLATE = "/v1/push/users/{pubkey}/errors/{errorId}"
ERRORS_PULL_PATH_TEMPLATE = "/v1/pull/users/{pubkey}/errors/{errorId}"
ENCRYPTION_INFO = "octobot-error-data"


def _get_client_and_address() -> tuple[StarfishClient, str] | None:
    authenticator = authentication.Authenticator.get_instance_if_exists()
    if authenticator is None:
        return None
    authenticator.init_sync_client()
    if authenticator._sync_client is None:
        return None
    return authenticator._sync_client, authenticator._sync_address


def _generate_credentials() -> tuple[str, str]:
    error_secret = secrets.token_hex(32)
    salt = secrets.token_hex(16)
    return error_secret, salt


async def upload_error(
    client: StarfishClient,
    address: str,
    error: Exception,
    *,
    context: dict[str, Any] | None = None,
    error_id: str | None = None,
) -> dict[str, Any] | None:
    error_secret, salt = _generate_credentials()
    push_path = ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=address, errorId=salt)
    pull_path = ERRORS_PULL_PATH_TEMPLATE.format(pubkey=address, errorId=salt)

    payload: dict[str, Any] = {
        "id": error_id or str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "version": octobot.constants.LONG_VERSION,
        "message": str(error),
        "type": type(error).__name__,
        "traceback": traceback.format_exception(error),
    }
    if octobot.constants.COMMUNITY_BOT_ID:
        payload["bot_id"] = octobot.constants.COMMUNITY_BOT_ID
    if context:
        payload["context"] = context

    try:
        manager = SyncManager(
            client=client,
            pull_path=pull_path,
            push_path=push_path,
            encryption_secret=error_secret,
            encryption_salt=salt,
            encryption_info=ENCRYPTION_INFO,
        )
        result = await manager.push(payload)
        if result is not None:
            result["errorId"] = salt
            result["errorSecret"] = error_secret
        return result
    except Exception as push_error:
        logger.exception(push_error, True, f"Failed to upload error report: {push_error}")
        return None


async def share_logs(export_path: str) -> dict[str, Any] | None:
    result = _get_client_and_address()
    if result is None:
        logger.warning("Cannot share logs: no sync client configured")
        return None
    client, address = result

    error_secret, salt = _generate_credentials()
    push_path = ERRORS_PUSH_PATH_TEMPLATE.format(pubkey=address, errorId=salt)
    pull_path = ERRORS_PULL_PATH_TEMPLATE.format(pubkey=address, errorId=salt)

    zip_path = f"{export_path}.zip"
    try:
        shutil.make_archive(export_path, "zip", octobot.constants.LOGS_FOLDER)
        with open(zip_path, "rb") as f:
            logs_b64 = base64.b64encode(f.read()).decode("ascii")
    finally:
        if os.path.isfile(zip_path):
            os.remove(zip_path)

    payload: dict[str, Any] = {
        "id": f"logs-{uuid.uuid4()}",
        "timestamp": int(time.time() * 1000),
        "version": octobot.constants.LONG_VERSION,
        "message": "User shared logs",
        "type": "logs",
        "logs_zip_b64": logs_b64,
    }
    if octobot.constants.COMMUNITY_BOT_ID:
        payload["bot_id"] = octobot.constants.COMMUNITY_BOT_ID

    try:
        manager = SyncManager(
            client=client,
            pull_path=pull_path,
            push_path=push_path,
            encryption_secret=error_secret,
            encryption_salt=salt,
            encryption_info=ENCRYPTION_INFO,
        )
        result = await manager.push(payload)
        if result is not None:
            result["errorId"] = salt
            result["errorSecret"] = error_secret
        return result
    except Exception as push_error:
        logger.exception(push_error, True, f"Failed to share logs: {push_error}")
        return None
