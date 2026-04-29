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

"""Nonce replay protection."""


import octobot_sync.auth.storage as storage_module


class NonceStore:
    def __init__(self, store: storage_module.AbstractStorageAdapter) -> None:
        self._store = store

    async def nonce_insert(self, nonce: str, pubkey: str) -> bool:
        """Returns True if nonce is fresh (allow request).
        Returns False if nonce was already seen within the 30s window (reject as replay).
        """
        return await self._store.set_if_absent(f"nonce:{pubkey}:{nonce}", "1", 30_000)
