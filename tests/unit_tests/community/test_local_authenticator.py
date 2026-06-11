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

import json
import os

import mock
import pytest

import octobot.constants as octobot_constants
import octobot.community.local_authenticator as local_authenticator_module
import octobot.community.supabase_backend.configuration_storage as configuration_storage_module
import octobot.community.wallet_backend as wallet_backend_module
import octobot_sync.auth as sync_auth


class TestGetUserConfiguration:
    def test_loads_community_wallets_from_user_config(self, tmp_path):
        wallet_address = "0xd9eeee68cb71d51f74ee1e5c3c78770ed5a2f1c3"
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "community": {
                        "wallets": {
                            octobot_constants.CHAIN_TYPE: {
                                octobot_constants.CHAIN_NETWORK: [
                                    {
                                        "address": wallet_address,
                                        "private_key": "abc123",
                                        "passphrase_hash": "salt:hash",
                                        "is_admin": True,
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        with mock.patch(
            "octobot_commons.configuration.config_file_manager.get_user_config",
            return_value=str(config_path),
        ):
            configuration = local_authenticator_module.get_user_configuration()

        assert configuration.config["community"]["wallets"][octobot_constants.CHAIN_TYPE][
            octobot_constants.CHAIN_NETWORK
        ][0]["address"] == wallet_address

        sync_storage = configuration_storage_module.SyncConfigurationStorage(configuration)
        wallet_backend = wallet_backend_module.WalletBackend(sync_storage, mock.Mock())
        loaded_wallet = wallet_backend.get_wallet_for_bot(wallet_address)
        assert loaded_wallet.address.lower() == wallet_address

    def test_get_wallet_by_user_id_resolves_by_derived_identity(self, tmp_path):
        private_key = "aa" * 32
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "community": {
                        "wallets": {
                            octobot_constants.CHAIN_TYPE: {
                                octobot_constants.CHAIN_NETWORK: [
                                    {
                                        "address": "0xd9eeee68cb71d51f74ee1e5c3c78770ed5a2f1c3",
                                        "private_key": private_key,
                                        "passphrase_hash": "salt:hash",
                                        "is_admin": True,
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        with mock.patch(
            "octobot_commons.configuration.config_file_manager.get_user_config",
            return_value=str(config_path),
        ):
            configuration = local_authenticator_module.get_user_configuration()

        sync_storage = configuration_storage_module.SyncConfigurationStorage(configuration)
        wallet_backend = wallet_backend_module.WalletBackend(sync_storage, mock.Mock())
        user_id = sync_auth.derive_user_id(private_key)
        wallet = wallet_backend.get_wallet_by_user_id(user_id)
        assert wallet.private_key == private_key
        with pytest.raises(wallet_backend_module.WalletNotFoundError):
            wallet_backend.get_wallet_by_user_id("not-a-known-user-id")

    def test_save_is_disabled(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        with mock.patch(
            "octobot_commons.configuration.config_file_manager.get_user_config",
            return_value=str(config_path),
        ):
            configuration = local_authenticator_module.get_user_configuration()

        configuration.save()
        assert config_path.read_text(encoding="utf-8") == "{}"


class TestGetStatelessConfiguration:
    def test_returns_empty_config(self):
        configuration = local_authenticator_module.get_stateless_configuration()
        assert configuration.config == {}
