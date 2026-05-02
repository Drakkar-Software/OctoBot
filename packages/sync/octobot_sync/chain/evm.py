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

from web3 import Web3


@dataclass
class Wallet:
    private_key: str
    address: str


def _eip191_hash(text: str) -> bytes:
    msg_bytes = text.encode("utf-8")
    prefix = f"\x19Ethereum Signed Message:\n{len(msg_bytes)}".encode("utf-8")
    return Web3.keccak(prefix + msg_bytes)


def create_evm_wallet() -> Wallet:
    account = Web3().eth.account.create()
    return Wallet(
        private_key=account.key.hex(),
        address=account.address,
    )


def address_from_evm_key(private_key: str) -> str:
    return Web3().eth.account.from_key(private_key).address


def verify_evm(canonical: str, signature: str, address: str) -> bool:
    try:
        msg_hash = _eip191_hash(canonical)
        recovered = Web3().eth.account._recover_hash(msg_hash, signature=signature)
        return recovered.lower() == address.lower()
    except Exception:
        return False
