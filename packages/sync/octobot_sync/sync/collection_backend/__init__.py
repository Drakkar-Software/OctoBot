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


import octobot_sync.sync.collection_backend.abstract_local_collection_provider as abstract_local_collection_provider_module
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_local_collection_storage_module
import octobot_sync.sync.collection_backend.base_local_collection_provider as base_local_collection_provider_module
import octobot_sync.sync.collection_backend.single_item_local_collection_storage as single_item_local_collection_storage_module
import octobot_sync.sync.collection_backend.single_item_local_collection_provider as single_item_local_collection_provider_module
import octobot_sync.sync.collection_backend.errors as errors_module

AbstractLocalCollectionProvider = abstract_local_collection_provider_module.AbstractLocalCollectionProvider
BaseLocalCollectionStorage = base_local_collection_storage_module.BaseLocalCollectionStorage
BaseLocalCollectionProvider = base_local_collection_provider_module.BaseLocalCollectionProvider
SingleItemLocalCollectionStorage = single_item_local_collection_storage_module.SingleItemLocalCollectionStorage
SingleItemLocalCollectionProvider = single_item_local_collection_provider_module.SingleItemLocalCollectionProvider
CollectionStorageError = errors_module.CollectionStorageError
CollectionDecryptionError = errors_module.CollectionDecryptionError
CollectionFileFormatError = errors_module.CollectionFileFormatError
ItemNotFoundError = errors_module.ItemNotFoundError
DuplicateItemError = errors_module.DuplicateItemError

__all__ = [
    "AbstractLocalCollectionProvider",
    "BaseLocalCollectionStorage",
    "BaseLocalCollectionProvider",
    "SingleItemLocalCollectionStorage",
    "SingleItemLocalCollectionProvider",
    "CollectionStorageError",
    "CollectionDecryptionError",
    "CollectionFileFormatError",
    "ItemNotFoundError",
    "DuplicateItemError",
]
