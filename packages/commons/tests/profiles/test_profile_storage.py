#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import os

import mock
import pytest

import octobot_commons.constants as constants
import octobot_commons.errors as errors_module
import octobot_commons.profiles.profile_types.profile as profile_module
import octobot_commons.profiles.backends as profile_backends_module
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_storage as profile_storage_module
import octobot_commons.profiles.profile_types.sync_profile as sync_profile_module


class TestProfileStorageListProfiles:
    def test_filesystem_profile_wins_on_id_conflict(self, tmp_path):
        profiles_path = os.path.join(tmp_path, constants.PROFILES_FOLDER)
        os.makedirs(profiles_path, exist_ok=True)
        default_profile_path = os.path.join(profiles_path, constants.DEFAULT_PROFILE)
        os.makedirs(default_profile_path, exist_ok=True)
        profile_file = {
            constants.CONFIG_PROFILE: {
                constants.CONFIG_ID: constants.DEFAULT_PROFILE,
                constants.CONFIG_NAME: "filesystem-default",
            },
            constants.PROFILE_CONFIG: {
                constants.CONFIG_CRYPTO_CURRENCIES: {},
                constants.CONFIG_EXCHANGES: {},
                constants.CONFIG_TRADER: {constants.CONFIG_ENABLED_OPTION: False},
                constants.CONFIG_SIMULATOR: {
                    constants.CONFIG_ENABLED_OPTION: True,
                    constants.CONFIG_STARTING_PORTFOLIO: {},
                    constants.CONFIG_SIMULATOR_FEES: {},
                },
                constants.CONFIG_TRADING: {
                    constants.CONFIG_TRADER_REFERENCE_MARKET: constants.DEFAULT_REFERENCE_MARKET,
                    constants.CONFIG_TRADER_RISK: 1,
                },
                constants.CONFIG_DISTRIBUTION: constants.DEFAULT_DISTRIBUTION,
            },
        }
        import octobot_commons.json_util as json_util

        json_util.safe_dump(profile_file, os.path.join(default_profile_path, constants.PROFILE_CONFIG_FILE))

        sync_profile_data = profile_data_module.ProfileData.from_dict(
            {
                "profile_details": {"id": constants.DEFAULT_PROFILE, "name": "sync-default"},
                "trading": {"reference_market": constants.DEFAULT_REFERENCE_MARKET},
            }
        )
        sync_profile = sync_profile_module.SyncProfile(
            sync_profile_data,
            os.path.join(tmp_path, "runtime", constants.DEFAULT_PROFILE),
        )
        filesystem_backend = mock.Mock()
        filesystem_backend.list_profiles.return_value = {
            constants.DEFAULT_PROFILE: profile_module.Profile(default_profile_path)
        }
        filesystem_backend.list_profiles.return_value[
            constants.DEFAULT_PROFILE
        ] = profile_backends_module.FilesystemProfileBackend().read_profile_from_path(
            default_profile_path
        )
        sync_backend = mock.Mock()
        sync_backend.list_profiles.return_value = {constants.DEFAULT_PROFILE: sync_profile}
        profile_storage = profile_storage_module.ProfileStorage(
            profiles_path,
            None,
            filesystem_backend=filesystem_backend,
            sync_backend=sync_backend,
        )
        profiles = profile_storage._list_profiles()
        assert profiles[constants.DEFAULT_PROFILE].name == "filesystem-default"


class TestProfileStorageConfigureSyncUser:
    def test_configure_sync_user_validates_wallet(self, profile_storage, monkeypatch):
        authenticator = mock.Mock()
        authenticator.get_wallet_by_user_id.return_value = mock.Mock()
        monkeypatch.setattr(
            "octobot_commons.authentication.Authenticator.instance",
            mock.Mock(return_value=authenticator),
        )
        profile_storage.configure_sync_user("wallet-user")
        assert profile_storage.is_sync_available()
        authenticator.get_wallet_by_user_id.assert_called_once_with("wallet-user")


class TestSyncProfileBackendImportProfileData:
    def test_import_profile_data_assigns_strategy_id(self, tmp_path):
        sync_backend = profile_backends_module.SyncProfileBackend(
            sync_user_id="wallet-user"
        )
        profile_data = profile_data_module.ProfileData.from_dict(
            {
                "profile_details": {"name": "my-profile"},
                "trading": {"reference_market": constants.DEFAULT_REFERENCE_MARKET},
            }
        )
        created_profile = None

        def _create_item(user_id, strategy):
            nonlocal created_profile
            assert user_id == "wallet-user"
            assert strategy.id == profile_data.profile_details.id
            created_profile = strategy
            return strategy

        import octobot_sync.sync.collection_backend.errors as collection_errors

        strategy_provider = mock.Mock()
        strategy_provider.update_item.side_effect = collection_errors.ItemNotFoundError(
            "missing"
        )
        strategy_provider.create_item.side_effect = _create_item
        with mock.patch.object(
            sync_backend,
            "_get_strategy_provider",
            mock.Mock(return_value=strategy_provider),
        ):
            profile = sync_backend.import_profile_data(
                profile_data,
                schema_path=None,
                name="my-profile",
            )
        assert profile.is_sync_backed()
        assert profile.profile_id == profile_data.profile_details.id
        assert created_profile is not None


class TestSyncProfileBackendDuplicateProfile:
    def test_duplicate_profile_assigns_new_strategy_id(self, profile):
        sync_backend = profile_backends_module.SyncProfileBackend(
            sync_user_id="wallet-user"
        )
        created_strategy_id = None

        def _create_item(user_id, strategy):
            nonlocal created_strategy_id
            assert user_id == "wallet-user"
            created_strategy_id = strategy.id
            return strategy

        import octobot_sync.sync.collection_backend.errors as collection_errors

        strategy_provider = mock.Mock()
        strategy_provider.update_item.side_effect = collection_errors.ItemNotFoundError(
            "missing"
        )
        strategy_provider.create_item.side_effect = _create_item
        with mock.patch.object(
            sync_backend,
            "_get_strategy_provider",
            mock.Mock(return_value=strategy_provider),
        ):
            duplicate = sync_backend.duplicate_profile(
                profile,
                name="copy-name",
                description="copy-desc",
            )
        assert duplicate.is_sync_backed()
        assert duplicate.profile_id == created_strategy_id
        assert duplicate.profile_id != profile.profile_id
        assert duplicate.name == "copy-name"
        assert duplicate.description == "copy-desc"
        assert duplicate.read_only is False
        assert duplicate.imported is False
        assert duplicate.origin_url is None


class TestProfileStorageListProfileIdsMerge:
    def test_list_profile_ids_merges_filesystem_and_sync_ids(self):
        filesystem_backend = mock.Mock()
        filesystem_backend.list_profile_ids.return_value = ["fs-profile"]
        sync_backend = mock.Mock()
        sync_backend.list_profile_ids.return_value = ["sync-profile", "fs-profile"]
        profile_storage = profile_storage_module.ProfileStorage(
            "/profiles",
            None,
            filesystem_backend=filesystem_backend,
            sync_backend=sync_backend,
        )
        profile_ids = profile_storage.list_profile_ids()
        assert profile_ids == ["fs-profile", "sync-profile"]
        filesystem_backend.list_profile_ids.assert_called_once_with(ignore=None)
        sync_backend.list_profile_ids.assert_called_once_with(ignore=None)


class TestProfileStorageDuplicateProfile:
    def test_duplicate_profile_requires_sync(self, profile_storage, profile):
        with pytest.raises(
            errors_module.ProfileDataError,
            match="configured wallet user id",
        ):
            profile_storage.duplicate_profile(profile)

    def test_duplicate_profile_delegates_to_sync_backend(
        self, profile_storage, profile, monkeypatch
    ):
        authenticator = mock.Mock()
        authenticator.get_wallet_by_user_id.return_value = mock.Mock()
        monkeypatch.setattr(
            "octobot_commons.authentication.Authenticator.instance",
            mock.Mock(return_value=authenticator),
        )
        profile_storage.configure_sync_user("wallet-user")
        sync_duplicate = mock.Mock()
        sync_duplicate.bind_profile_storage = mock.Mock()
        sync_backend = mock.Mock()
        sync_backend.duplicate_profile.return_value = sync_duplicate
        profile_storage._sync_backend = sync_backend
        result = profile_storage.duplicate_profile(
            profile, name="copy", description="desc"
        )
        sync_backend.duplicate_profile.assert_called_once_with(
            profile,
            name="copy",
            description="desc",
        )
        sync_duplicate.bind_profile_storage.assert_called_once_with(profile_storage)
        assert result is sync_duplicate
