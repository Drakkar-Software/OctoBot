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

import time
import uuid

from web3 import Web3

import octobot_sync.auth.canonical as canonical
import octobot_sync.chain.evm as evm
import octobot_sync.constants as constants


class SatelliteAuthProvider:
    def __init__(self, private_key: str, chain_id: str) -> None:
        self._w3 = Web3()
        self._private_key = private_key
        self._address = evm.address_from_evm_key(private_key)
        self._chain_id = chain_id

    @property
    def address(self) -> str:
        return self._address

    async def __call__(
        self, *, method: str, path: str, body: str | None
    ) -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        body_hash = canonical.hash_body(body)
        msg = canonical.build_canonical(method, path, ts, nonce, body_hash)
        msg_hash = evm._eip191_hash(msg)
        signed = self._w3.eth.account._sign_hash(msg_hash, private_key=self._private_key)
        return {
            constants.HEADER_PUBKEY: self._address,
            constants.HEADER_SIGNATURE: signed.signature.hex(),
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: nonce,
            constants.HEADER_CHAIN: self._chain_id,
        }
