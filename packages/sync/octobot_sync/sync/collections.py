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

from satellite_server.config.loader import load_config_file
from satellite_server.config.schema import SyncConfig, CollectionConfig

import octobot_sync.constants as constants

logger = logging.get_logger("SyncCollections")

DEFAULT_SYNC_CONFIG = SyncConfig(
    version=1,
    collections=[
        CollectionConfig(
            name="bots",
            storagePath="users/{identity}",
            bundle="user-data",
            readRoles=["self"],
            writeRoles=["self"],
            encryption="identity",
            maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
        ),
        CollectionConfig(
            name="accounts",
            storagePath="users/{identity}",
            bundle="user-data",
            readRoles=["self"],
            writeRoles=["self"],
            encryption="identity",
            maxBodyBytes=constants.MAX_BODY_SIZE_PRIVATE,
        ),
        CollectionConfig(
            name="errors",
            storagePath="users/{identity}/errors/{errorId}",
            readRoles=["admin"],
            writeRoles=["user"],
            encryption="delegated",
            maxBodyBytes=constants.MAX_BODY_SIZE_SIGNAL,
        ),
    ],
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
