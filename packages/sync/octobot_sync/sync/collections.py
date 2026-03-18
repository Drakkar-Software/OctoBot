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
from starfish_server.config.schema import SyncConfig, CollectionConfig, RemoteConfig, WriteMode, SyncTrigger

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


def is_replicable_collection(col: CollectionConfig) -> bool:
    """A collection is replicable if its storagePath has no template variables."""
    return "{" not in col.storage_path


def make_replica_config(
    config: SyncConfig,
    primary_url: str,
    write_mode: str = "bidirectional",
    sync_interval_ms: int = 60_000,
) -> tuple[SyncConfig, list[CollectionConfig]]:
    """Inject RemoteConfig into replicable collections.

    Returns the updated SyncConfig (with remote on replicable collections)
    and the list of non-replicable (proxy) collections.
    """
    mode = WriteMode(write_mode)
    replicable = []
    proxied = []
    for col in config.collections:
        if is_replicable_collection(col):
            col_with_remote = col.model_copy(
                update={
                    "remote": RemoteConfig(
                        url=primary_url,
                        pullPath=f"/pull/{col.storage_path}",
                        pushPath=f"/push/{col.storage_path}" if mode != WriteMode.PULL_ONLY else None,
                        writeMode=mode,
                        intervalMs=sync_interval_ms,
                        syncTriggers=[SyncTrigger.ON_PULL, SyncTrigger.SCHEDULED],
                    ),
                }
            )
            replicable.append(col_with_remote)
        else:
            proxied.append(col)
    updated_config = config.model_copy(update={"collections": replicable + proxied})
    return updated_config, proxied
