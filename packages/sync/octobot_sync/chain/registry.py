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

import octobot_sync.chain.interface as chain_interface


class ChainRegistry:
    def __init__(self) -> None:
        self._chains: dict[str, chain_interface.AbstractChain] = {}

    def register(self, chain: chain_interface.AbstractChain) -> None:
        self._chains[chain.id] = chain

    def get(self, chain_id: str) -> chain_interface.AbstractChain:
        chain = self._chains.get(chain_id)
        if chain is None:
            raise ValueError(f"Unknown chain: {chain_id}")
        return chain

    def list(self) -> list[chain_interface.AbstractChain]:
        return list(self._chains.values())
