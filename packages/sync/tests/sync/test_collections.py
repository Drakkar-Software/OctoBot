#  Drakkar-Software OctoBot-Sync
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

import octobot_sync.constants as sync_constants
import octobot_sync.sync.collections as collections_module
import starfish_server.config.schema as schema_module


def _make_collection_config(storage_path: str) -> schema_module.CollectionConfig:
    return schema_module.CollectionConfig(
        name="test-collection",
        storagePath=storage_path,
        readRoles=["self"],
        writeRoles=["self"],
        encryption="delegated",
        maxBodyBytes=sync_constants.MAX_BODY_SIZE_PRIVATE,
    )


class TestIsReplicableCollection:
    def test_true_when_storage_path_has_no_placeholders(self):
        collection_config = _make_collection_config("users/data")

        assert collections_module.is_replicable_collection(collection_config) is True

    def test_false_when_storage_path_contains_identity_placeholder(self):
        collection_config = _make_collection_config("users/{identity}/data")

        assert collections_module.is_replicable_collection(collection_config) is False

    def test_false_when_storage_path_contains_account_id_placeholder(self):
        collection_config = _make_collection_config(
            "users/{identity}/accounts/{account_id}/trading"
        )

        assert collections_module.is_replicable_collection(collection_config) is False
