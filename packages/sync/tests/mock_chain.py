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

"""MockChain — in-memory AbstractChain for testing."""


import time

import octobot_sync.chain.interface as chain_interface


class MockChain:
    def __init__(self, chain_id: str = "mock") -> None:
        self._id = chain_id
        self._items: dict[str, chain_interface.Item] = {}
        self._owners: dict[str, str] = {}
        self._signatures: dict[str, bool] = {}
        self._access: list[dict] = []

    @property
    def id(self) -> str:
        return self._id



    def set_item(self, item_id: str, item: chain_interface.Item) -> None:
        self._items[item_id] = item

    def set_owner(self, item_id: str, owner: str) -> None:
        self._owners[item_id] = owner

    def set_signature_valid(
        self, canonical: str, signature: str, pubkey: str, valid: bool
    ) -> None:
        self._signatures[f"{canonical}:{signature}:{pubkey}"] = valid

    def set_access(self, item_id: str, user_address: str, expires_at: int) -> None:
        self._access.append(
            {"user": user_address, "itemId": item_id, "expiresAt": expires_at}
        )



    async def verify_signature(
        self, canonical: str, signature: str, pubkey_or_address: str
    ) -> bool:
        return self._signatures.get(f"{canonical}:{signature}:{pubkey_or_address}", False)

    async def get_item(self, item_id: str) -> chain_interface.Item | None:
        return self._items.get(item_id)

    async def is_item_owner(self, item_id: str, pubkey_or_address: str) -> bool:
        owner = self._owners.get(item_id)
        return owner == pubkey_or_address

    async def has_access(self, item_id: str, user_address: str) -> bool:
        entry = None
        for a in self._access:
            if a["user"] == user_address and a["itemId"] == item_id:
                entry = a
        if entry is None:
            return False
        return entry["expiresAt"] == 0 or entry["expiresAt"] > time.time()
