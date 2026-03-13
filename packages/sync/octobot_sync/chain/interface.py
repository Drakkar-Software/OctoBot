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

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Item:
    id: str
    owner: str


@dataclass
class Wallet:
    private_key: str
    address: str


class AbstractChain(Protocol):
    @property
    def id(self) -> str: ...

    @staticmethod
    def create_wallet() -> Wallet: ...

    @staticmethod
    def address_from_key(private_key: str) -> str: ...

    async def verify_signature(
        self, canonical: str, signature: str, pubkey_or_address: str
    ) -> bool: ...

    async def get_item(self, item_id: str) -> Item | None: ...

    async def is_item_owner(self, item_id: str, pubkey_or_address: str) -> bool: ...

    async def has_access(self, item_id: str, user_address: str) -> bool: ...
