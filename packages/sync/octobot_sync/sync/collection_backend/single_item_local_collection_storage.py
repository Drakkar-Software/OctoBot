#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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


import pathlib

import octobot_sync.sync.collection_backend.base_local_collection_storage as base_local_collection_storage
import octobot_sync.sync.collection_backend.errors as collection_errors


class SingleItemLocalCollectionStorage(base_local_collection_storage.BaseLocalCollectionStorage):
    """
    Encrypted collection storage keyed by a composite identifier.

    State is persisted at ``<user_root>/<collection>/<identifier>.json`` where
    *identifier* is typically ``<user_id>/<account_id>`` with each segment
    sanitized separately (nested directories under the collection root).
    """

    def _file_path(self, identifier: str) -> pathlib.Path:
        path_parts = [
            self._sanitize_storage_key(part)
            for part in identifier.split("/")
            if part
        ]
        if not path_parts:
            path_parts = ["unknown"]
        directory_parts = path_parts[:-1]
        filename = f"{path_parts[-1]}.json"
        path = self._root
        for directory_part in directory_parts:
            path = path / directory_part
        return path / filename

    def _missing_data_error(self, identifier: str) -> collection_errors.CollectionNoDataError:
        return collection_errors.CollectionNoDataError(
            f"{self.collection} file does not exist for identifier {identifier}"
        )
