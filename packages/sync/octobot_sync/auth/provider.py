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

import web3

import octobot_sync.auth.canonical as canonical
import octobot_sync.constants as constants


class StarfishAuthProvider:
    def __init__(self, private_key: str) -> None:
        self._private_key = private_key
        self._address = web3.Account.from_key(private_key).address  # pylint: disable=no-value-for-parameter

    @property
    def address(self) -> str:
        return self._address

    async def sign_payload(self, data: str) -> str:
        signed = web3.Account.sign_message(canonical.eip191_message(data), private_key=self._private_key)  # pylint: disable=no-value-for-parameter
        return signed.signature.hex()

    async def __call__(
        self, *, method: str, path: str, body: str | None
    ) -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        body_hash = canonical.hash_body(body)
        msg = canonical.build_canonical(method, path, ts, nonce, body_hash)
        signed = web3.Account.sign_message(canonical.eip191_message(msg), private_key=self._private_key)  # pylint: disable=no-value-for-parameter
        return {
            constants.HEADER_PUBKEY: self._address,
            constants.HEADER_SIGNATURE: signed.signature.hex(),
            constants.HEADER_TIMESTAMP: ts,
            constants.HEADER_NONCE: nonce,
        }
