#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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
import base64
import typing

import octobot_commons.cryptography.encryption as commons_encryption

import octobot.constants as constants
import octobot_sync.chain as sync_chain


class WalletBackend:
    def __init__(self, sync_storage, logger):
        self._sync_storage = sync_storage
        self.logger = logger

    def get_or_create_wallet_private_key(self, chain_id: str) -> typing.Optional[str]:
        chain_type, chain_network = chain_id.split(":", 1)
        wallets = self._sync_storage.get_item(constants.CONFIG_COMMUNITY_WALLETS) or {}
        chain_wallets = wallets.get(chain_type, {})
        private_key = chain_wallets.get(chain_network)
        if isinstance(private_key, dict):
            # Encrypted keystore — plaintext key unavailable without passphrase
            return None
        if private_key:
            return private_key
        wallet = sync_chain.create_evm_wallet()
        chain_wallets[chain_network] = wallet.private_key
        wallets[chain_type] = chain_wallets
        self._sync_storage.set_item(constants.CONFIG_COMMUNITY_WALLETS, wallets)
        self.logger.info(f"Created new {chain_type} wallet for {chain_id}: {wallet.address}")
        return wallet.private_key

    def _get_node_keystore(self) -> dict:
        chain_type, chain_network = constants.SYNC_CHAIN_ID.split(":", 1)
        wallets = self._sync_storage.get_item(constants.CONFIG_COMMUNITY_WALLETS) or {}
        value = wallets.get(chain_type, {}).get(chain_network)
        if isinstance(value, dict):
            return value
        return {}

    def _save_node_keystore(self, keystore: dict) -> None:
        chain_type, chain_network = constants.SYNC_CHAIN_ID.split(":", 1)
        wallets = self._sync_storage.get_item(constants.CONFIG_COMMUNITY_WALLETS) or {}
        chain_wallets = wallets.get(chain_type, {})
        chain_wallets[chain_network] = keystore
        wallets[chain_type] = chain_wallets
        self._sync_storage.set_item(constants.CONFIG_COMMUNITY_WALLETS, wallets)

    def is_node_wallet_configured(self) -> bool:
        try:
            return bool(self._get_node_keystore().get("encrypted_key"))
        except Exception:
            return False

    def get_node_wallet_address(self) -> typing.Optional[str]:
        try:
            return self._get_node_keystore().get("address") or None
        except Exception:
            return None

    def create_and_encrypt_node_wallet(self, passphrase: str) -> sync_chain.Wallet:
        wallet = sync_chain.create_evm_wallet()
        key_bytes = bytes.fromhex(wallet.private_key.removeprefix("0x"))
        encrypted_key, salt, iv = commons_encryption.pbkdf2_encrypt_aes_key(key_bytes, passphrase)
        self._save_node_keystore({
            "address": wallet.address,
            "encrypted_key": base64.b64encode(encrypted_key).decode(),
            "salt": base64.b64encode(salt).decode(),
            "iv": base64.b64encode(iv).decode(),
        })
        return wallet

    def import_and_encrypt_node_wallet(self, private_key: str, passphrase: str) -> sync_chain.Wallet:
        try:
            address = sync_chain.address_from_evm_key(private_key)
        except Exception as err:
            raise ValueError(f"Invalid EVM private key: {err}") from err
        key_bytes = bytes.fromhex(private_key.removeprefix("0x"))
        encrypted_key, salt, iv = commons_encryption.pbkdf2_encrypt_aes_key(key_bytes, passphrase)
        self._save_node_keystore({
            "address": address,
            "encrypted_key": base64.b64encode(encrypted_key).decode(),
            "salt": base64.b64encode(salt).decode(),
            "iv": base64.b64encode(iv).decode(),
        })
        return sync_chain.Wallet(private_key=private_key, address=address)

    def decrypt_node_wallet(self, passphrase: str) -> sync_chain.Wallet:
        keystore = self._get_node_keystore()
        encrypted_key = base64.b64decode(keystore["encrypted_key"])
        salt = base64.b64decode(keystore["salt"])
        iv = base64.b64decode(keystore["iv"])
        address = keystore["address"]
        key_bytes = commons_encryption.pbkdf2_decrypt_aes_key(encrypted_key, passphrase, salt, iv)
        return sync_chain.Wallet(private_key=key_bytes.hex(), address=address)

    def verify_node_passphrase(self, passphrase: str) -> bool:
        try:
            self.decrypt_node_wallet(passphrase)
            return True
        except Exception:
            return False
