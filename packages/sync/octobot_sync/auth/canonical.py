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

import hashlib
import typing


# EIP-191 personal sign: keccak256("\x19Ethereum Signed Message:\n{byteLen}{msg}")
# web3's _hash_eip191_message prepends \x19 then joins version+header+body,
# so version must be b"E" (not b"\x19E") to avoid a double \x19 prefix.
# This NamedTuple duck-types eth_account.messages.SignableMessage so
# web3.Account.sign_message / recover_message accept it without any eth_account import.
class _EIP191Message(typing.NamedTuple):
    version: bytes
    header: bytes
    body: bytes


def eip191_message(text: str) -> _EIP191Message:
    msg = text.encode("utf-8")
    return _EIP191Message(
        version=b"E",
        header=b"thereum Signed Message:\n" + str(len(msg)).encode("utf-8"),
        body=msg,
    )


def build_canonical(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body_hash: str,
) -> str:
    return f"ED25519-OCTOBOT\n{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"


def hash_body(body: str | None) -> str:
    data = (body or "").encode("utf-8")
    return hashlib.sha256(data).hexdigest()
