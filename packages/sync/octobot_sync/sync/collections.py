#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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

import os

import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging

from starfish_server.config.loader import load_config_file
from starfish_server.config.schema import SyncConfig, CollectionConfig, NamespaceConfig

import octobot_sync.constants as constants
import octobot_sync.enums as enums

logger = logging.get_logger("Collections")

DEFAULT_SYNC_CONFIG = SyncConfig(
    version=1,
    collections=[],
    namespaces={
        constants.SYNC_NAMESPACE: NamespaceConfig(
            collections=[
                CollectionConfig(
                    name=enums.Collections.USER_DATA.value,
                    storagePath="users/{identity}/data",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                CollectionConfig(
                    name=enums.Collections.USER_ACCOUNTS.value,
                    storagePath="users/{identity}/accounts",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                CollectionConfig(
                    name=enums.Collections.USER_ACCOUNTS_AUTH.value,
                    storagePath="users/{identity}/accounts/auth",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                CollectionConfig(
                    name=enums.Collections.USER_ACCOUNTS_TRADING.value,
                    storagePath="users/{identity}/accounts/{account_id}/trading",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                CollectionConfig(
                    name=enums.Collections.USER_ACCOUNTS_HISTORY.value,
                    storagePath="users/{identity}/accounts/{account_id}/history",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                CollectionConfig(
                    name=enums.Collections.USER_SETTINGS.value,
                    storagePath="users/{identity}/settings",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                CollectionConfig(
                    name=enums.Collections.USER_STRATEGIES.value,
                    storagePath="users/{identity}/strategies",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                ),
                CollectionConfig(
                    name=enums.Collections.USER_ACTIONS.value,
                    storagePath="users/{identity}/actions",
                    readRoles=["self"],
                    writeRoles=["self"],
                    encryption="delegated",
                    maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
                )
            ]
        )
    },
)


def load_sync_config(
    collections_path: str | None = None,
) -> SyncConfig:
    path = collections_path or os.path.join(
        commons_constants.USER_FOLDER, constants.COLLECTIONS_FILE
    )
    if not os.path.isfile(path):
        logger.warning(
            f"Collections file not found at {path}, using default config"
        )
        return DEFAULT_SYNC_CONFIG
    return load_config_file(path)


def is_replicable_collection(col: CollectionConfig) -> bool:
    return "{" not in col.storage_path
