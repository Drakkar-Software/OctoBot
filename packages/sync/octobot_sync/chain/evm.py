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

import functools

from cachetools import TTLCache
from web3 import Web3, AsyncWeb3
from web3.providers import AsyncHTTPProvider

import octobot_sync.chain.interface as chain_interface

_SENTINEL = object()


def _async_ttl_cached(ttl_s: float, maxsize: int = 1024):
    def decorator(fn):
        cache = TTLCache(maxsize=maxsize, ttl=ttl_s)

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = args[1:]  # skip self
            result = cache.get(key, _SENTINEL)
            if result is not _SENTINEL:
                return result
            result = await fn(*args, **kwargs)
            cache[key] = result
            return result

        wrapper.cache = cache
        return wrapper

    return decorator

OCTOBOT_PRODUCT_ABI = [
    {
        "type": "function",
        "name": "ownerOf",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "owner", "type": "address"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "hasAccess",
        "inputs": [
            {"name": "user", "type": "address"},
            {"name": "itemId", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
]


def _eip191_hash(text: str) -> bytes:
    """Compute the EIP-191 personal_sign message hash without eth_account."""
    msg_bytes = text.encode("utf-8")
    prefix = f"\x19Ethereum Signed Message:\n{len(msg_bytes)}".encode("utf-8")
    return Web3.keccak(prefix + msg_bytes)


def create_evm_wallet() -> chain_interface.Wallet:
    account = Web3().eth.account.create()
    return chain_interface.Wallet(
        private_key=account.key.hex(),
        address=account.address,
    )


def address_from_evm_key(private_key: str) -> str:
    return Web3().eth.account.from_key(private_key).address


def verify_evm(canonical: str, signature: str, address: str) -> bool:
    """Verify an EIP-191 personal_sign signature via web3."""
    try:
        msg_hash = _eip191_hash(canonical)
        recovered = Web3().eth.account._recover_hash(msg_hash, signature=signature)
        return recovered.lower() == address.lower()
    except Exception:
        return False



class EvmChain:
    def __init__(
        self,
        chain_id: str,
        rpc_url: str | None = None,
        contract_address: str | None = None,
    ) -> None:
        self._id = chain_id
        if rpc_url and contract_address:
            self._contract_address = AsyncWeb3.to_checksum_address(contract_address)
            self._w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
            self._contract = self._w3.eth.contract(
                address=self._contract_address, abi=OCTOBOT_PRODUCT_ABI
            )
        else:
            self._contract = None

    @property
    def id(self) -> str:
        return self._id

    @staticmethod
    def create_wallet() -> chain_interface.Wallet:
        return create_evm_wallet()

    @staticmethod
    def address_from_key(private_key: str) -> str:
        return address_from_evm_key(private_key)

    async def verify_signature(
        self, canonical: str, signature: str, pubkey_or_address: str
    ) -> bool:
        return verify_evm(canonical, signature, pubkey_or_address)

    def _require_contract(self) -> None:
        if self._contract is None:
            raise RuntimeError(
                f"Chain {self._id}: RPC not configured. "
                "Set EVM_BASE_RPC and EVM_CONTRACT_BASE environment variables."
            )

    @_async_ttl_cached(ttl_s=30)
    async def get_item(self, item_id: str) -> chain_interface.Item | None:
        self._require_contract()
        try:
            owner = await self._contract.functions.ownerOf(int(item_id)).call()
            return chain_interface.Item(id=item_id, owner=owner)
        except Exception:
            return None

    @_async_ttl_cached(ttl_s=365 * 86400)
    async def is_item_owner(self, item_id: str, pubkey_or_address: str) -> bool:
        item = await self.get_item(item_id)
        return item is not None and item.owner.lower() == pubkey_or_address.lower()

    @_async_ttl_cached(ttl_s=60)
    async def has_access(self, item_id: str, user_address: str) -> bool:
        self._require_contract()
        return await self._contract.functions.hasAccess(
            AsyncWeb3.to_checksum_address(user_address), int(item_id)
        ).call()
