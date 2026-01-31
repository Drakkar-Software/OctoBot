# pylint: disable=R0801
#  Drakkar-Software OctoBot-Commons
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


from octobot_commons.databases import global_storage
from octobot_commons.databases import database_caches
from octobot_commons.databases import document_database_adaptors
from octobot_commons.databases import bases
from octobot_commons.databases import implementations
from octobot_commons.databases import relational_databases

from octobot_commons.databases import cache_manager
from octobot_commons.databases import databases_util
from octobot_commons.databases import cache_client
from octobot_commons.databases import run_databases

from octobot_commons.databases.global_storage import (
    GlobalSharedMemoryStorage,
)

from octobot_commons.databases.database_caches import (
    GenericDatabaseCache,
    ChronologicalReadDatabaseCache,
)

from octobot_commons.databases.document_database_adaptors import (
    AbstractDocumentDatabaseAdaptor,
    TinyDBAdaptor,
)

from octobot_commons.databases.bases import (
    DocumentDatabase,
    BaseDatabase,
)

from octobot_commons.databases.implementations import (
    DBReader,
    DBWriter,
    DBWriterReader,
    MetaDatabase,
    CacheDatabase,
    CacheTimestampDatabase,
)

from octobot_commons.databases.relational_databases import (
    SQLiteDatabase,
    new_sqlite_database,
)

from octobot_commons.databases.run_databases import (
    RunDatabasesIdentifier,
    RunDatabasesProvider,
    init_bot_storage,
    close_bot_storage,
    AbstractRunDatabasesPruner,
    FileSystemRunDatabasesPruner,
    run_databases_pruner_factory,
)

from octobot_commons.databases.cache_manager import (
    CacheManager,
)

from octobot_commons.databases.databases_util import (
    CacheWrapper,
)

from octobot_commons.databases.cache_client import (
    CacheClient,
)


__all__ = [
    "GlobalSharedMemoryStorage",
    "GenericDatabaseCache",
    "ChronologicalReadDatabaseCache",
    "AbstractDocumentDatabaseAdaptor",
    "TinyDBAdaptor",
    "DocumentDatabase",
    "BaseDatabase",
    "MetaDatabase",
    "DBReader",
    "DBWriter",
    "DBWriterReader",
    "CacheDatabase",
    "CacheTimestampDatabase",
    "SQLiteDatabase",
    "new_sqlite_database",
    "RunDatabasesIdentifier",
    "RunDatabasesProvider",
    "init_bot_storage",
    "close_bot_storage",
    "AbstractRunDatabasesPruner",
    "FileSystemRunDatabasesPruner",
    "run_databases_pruner_factory",
    "CacheManager",
    "CacheWrapper",
    "CacheClient",
]
