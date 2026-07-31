#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import asyncio
import os
import copy

import mock
import pytest

import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.errors as errors_module
import octobot_commons.json_util as json_util
import octobot_commons.profiles.profile_types.profile as profile_module
import octobot_commons.profiles.backends as profile_backends_module
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_storage as profile_storage_module
import octobot_commons.profiles.profile_types.sync_profile as sync_profile_module
import octobot_commons.profiles.profile_data_import as profile_data_import_module
import octobot_sync.sync.collection_backend.errors as collection_errors


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


class TestProfileStorageBindProcessChildSyncUserId:
    def test_bind_process_child_sync_user_id_sets_backend_without_wallet(self, profile_storage):
        profile_storage.bind_process_child_sync_user_id("process-child-user")
        assert profile_storage.is_sync_available()
        assert profile_storage._sync_user_id == "process-child-user"

    def test_bind_process_child_sync_user_id_rejects_empty(self, profile_storage):
        with pytest.raises(errors_module.ProfileDataError, match="non-empty"):
            profile_storage.bind_process_child_sync_user_id("")


class TestProfileStorageListSyncProfiles:
    def test_returns_empty_when_sync_unavailable(self, profile_storage):
        assert profile_storage.list_sync_profiles() == {}

    def test_returns_sync_profiles_with_storage_bound(self, profile_storage):
        sync_profile_data = profile_data_module.ProfileData.from_dict(
            {
                "profile_details": {"id": "sync-profile-id", "name": "sync-profile"},
                "trading": {"reference_market": constants.DEFAULT_REFERENCE_MARKET},
            }
        )
        sync_profile = sync_profile_module.SyncProfile(
            sync_profile_data,
            os.path.join(profile_storage.profiles_path, "runtime", "sync-profile-id"),
        )
        sync_backend = mock.Mock()
        sync_backend.list_profiles.return_value = {"sync-profile-id": sync_profile}
        profile_storage._sync_backend = sync_backend
        profile_storage.bind_process_child_sync_user_id("process-child-user")

        profiles_by_id = profile_storage.list_sync_profiles()

        sync_backend.list_profiles.assert_called_once_with(None)
        assert profiles_by_id == {"sync-profile-id": sync_profile}
        assert sync_profile.get_profile_storage() is profile_storage


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


class TestSyncProfileBackendListProfiles:
    def test_list_profiles_logs_exception_on_failure(self):
        sync_backend = profile_backends_module.SyncProfileBackend(
            "/profiles",
            sync_user_id="wallet-user",
        )
        with mock.patch.object(
            sync_backend,
            "_list_profile_strategies",
            mock.Mock(side_effect=RuntimeError("sync storage unavailable")),
        ), mock.patch(
            "octobot_commons.profiles.backends.sync_profile_backend._get_logger",
        ) as get_logger_mock:
            logger_mock = mock.Mock()
            get_logger_mock.return_value = logger_mock
            profiles_by_id = sync_backend.list_profiles()
        assert profiles_by_id == {}
        logger_mock.exception.assert_called_once()


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


class TestProfileStorageMasterOverlay:
    def _write_profile_file(self, profile_path: str, profile_id: str, *, read_only: bool) -> None:
        os.makedirs(profile_path, exist_ok=True)
        profile_file = {
            constants.CONFIG_PROFILE: {
                constants.CONFIG_ID: profile_id,
                constants.CONFIG_NAME: profile_id,
                constants.CONFIG_READ_ONLY: read_only,
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
        json_util.safe_dump(profile_file, os.path.join(profile_path, constants.PROFILE_CONFIG_FILE))

    def test_overlay_exposes_read_only_profiles(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        readonly_profile_id = "readonly-strategy"
        self._write_profile_file(
            os.path.join(master_profiles_path, readonly_profile_id),
            readonly_profile_id,
            read_only=True,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profiles = profile_storage.load_all_profiles()
        assert readonly_profile_id in profiles
        assert profiles[readonly_profile_id].read_only is True

    def test_overlay_exposes_editable_profiles(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        editable_profile_id = "editable-strategy"
        self._write_profile_file(
            os.path.join(master_profiles_path, editable_profile_id),
            editable_profile_id,
            read_only=False,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profiles = profile_storage.load_all_profiles()
        assert editable_profile_id in profiles
        assert profiles[editable_profile_id].read_only is False

    def test_local_filesystem_profile_wins_on_id_conflict(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        profile_id = "shared-id"
        child_profiles_path.mkdir(parents=True, exist_ok=True)
        self._write_profile_file(
            os.path.join(master_profiles_path, profile_id),
            profile_id,
            read_only=True,
        )
        self._write_profile_file(
            os.path.join(child_profiles_path, profile_id),
            profile_id,
            read_only=False,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profiles = profile_storage.load_all_profiles()
        assert profiles[profile_id].name == profile_id
        assert profiles[profile_id].path == os.path.join(child_profiles_path, profile_id)

    def test_save_active_profile_persists_readonly_master_overlay_to_child_path(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        readonly_profile_id = "non-trading"
        master_profile_path = os.path.join(master_profiles_path, readonly_profile_id)
        self._write_profile_file(
            master_profile_path,
            readonly_profile_id,
            read_only=True,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        overlay_profile = profile_storage.get_profile(readonly_profile_id)
        overlay_profile.config[constants.CONFIG_TRADER] = {
            constants.CONFIG_ENABLED_OPTION: True,
        }
        profile_storage.save_active_profile(overlay_profile, {})
        child_overlay_file = json_util.read_file(
            os.path.join(child_profiles_path, readonly_profile_id, constants.PROFILE_CONFIG_FILE)
        )
        master_profile_file = json_util.read_file(
            os.path.join(master_profile_path, constants.PROFILE_CONFIG_FILE)
        )
        assert (
            child_overlay_file[constants.PROFILE_CONFIG][constants.CONFIG_TRADER][
                constants.CONFIG_ENABLED_OPTION
            ]
            is True
        )
        assert (
            master_profile_file[constants.PROFILE_CONFIG][constants.CONFIG_TRADER][
                constants.CONFIG_ENABLED_OPTION
            ]
            is False
        )

    def test_load_all_profiles_excludes_child_overlay_only_entry(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        readonly_profile_id = "non-trading"
        master_profile_path = os.path.join(master_profiles_path, readonly_profile_id)
        self._write_profile_file(
            master_profile_path,
            readonly_profile_id,
            read_only=True,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profiles_before_save = profile_storage.load_all_profiles()
        assert set(profiles_before_save) == {readonly_profile_id}
        overlay_profile = profile_storage.get_profile(readonly_profile_id)
        overlay_profile.config[constants.CONFIG_TRADER] = {
            constants.CONFIG_ENABLED_OPTION: True,
        }
        profile_storage.save_active_profile(overlay_profile, {})
        filesystem_profiles = profile_storage._filesystem_backend.list_profiles()
        assert len(filesystem_profiles) == 1
        profiles_after_save = profile_storage.load_all_profiles()
        assert set(profiles_after_save) == {readonly_profile_id}
        assert (
            profiles_after_save[readonly_profile_id].config[constants.CONFIG_TRADER][
                constants.CONFIG_ENABLED_OPTION
            ]
            is True
        )

    def test_is_child_profile_config_overlay(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        readonly_profile_id = "non-trading"
        self._write_profile_file(
            os.path.join(master_profiles_path, readonly_profile_id),
            readonly_profile_id,
            read_only=True,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        overlay_profile = profile_storage.get_profile(readonly_profile_id)
        overlay_profile.config[constants.CONFIG_TRADER] = {
            constants.CONFIG_ENABLED_OPTION: True,
        }
        profile_storage.save_active_profile(overlay_profile, {})
        child_overlay_profile = next(
            iter(profile_storage._filesystem_backend.list_profiles().values())
        )
        master_profile = profile_storage.get_profile(readonly_profile_id)
        assert profile_storage.is_child_profile_config_overlay(child_overlay_profile) is True
        assert profile_storage.is_child_profile_config_overlay(master_profile) is False

    def test_is_child_profile_config_overlay_false_for_full_local_profile(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        profile_id = "shared-id"
        child_profiles_path.mkdir(parents=True, exist_ok=True)
        self._write_profile_file(
            os.path.join(master_profiles_path, profile_id),
            profile_id,
            read_only=True,
        )
        self._write_profile_file(
            os.path.join(child_profiles_path, profile_id),
            profile_id,
            read_only=False,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        profiles = profile_storage.load_all_profiles()
        assert profile_storage.is_child_profile_config_overlay(profiles[profile_id]) is False

    def test_save_active_profile_persists_editable_master_overlay_on_master_path(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        editable_profile_id = "editable-strategy"
        master_profile_path = os.path.join(master_profiles_path, editable_profile_id)
        self._write_profile_file(
            master_profile_path,
            editable_profile_id,
            read_only=False,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        overlay_profile = profile_storage.get_profile(editable_profile_id)
        overlay_profile.config[constants.CONFIG_TRADER] = {
            constants.CONFIG_ENABLED_OPTION: True,
        }
        profile_storage.save_active_profile(overlay_profile, {})
        master_profile_file = json_util.read_file(
            os.path.join(master_profile_path, constants.PROFILE_CONFIG_FILE)
        )
        assert (
            master_profile_file[constants.PROFILE_CONFIG][constants.CONFIG_TRADER][
                constants.CONFIG_ENABLED_OPTION
            ]
            is True
        )
        assert not os.path.isdir(os.path.join(child_profiles_path, editable_profile_id))

    def test_delete_profile_blocks_master_overlay_profile(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        readonly_profile_id = "readonly-strategy"
        self._write_profile_file(
            os.path.join(master_profiles_path, readonly_profile_id),
            readonly_profile_id,
            read_only=True,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        overlay_profile = profile_storage.get_profile(readonly_profile_id)
        with pytest.raises(
            errors_module.ProfileRemovalError,
            match="shared from the master",
        ):
            profile_storage.delete_profile(readonly_profile_id, profile=overlay_profile)

    def test_delete_profile_removes_editable_master_overlay_from_master_path(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        child_profiles_path.mkdir(parents=True)
        master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
        editable_profile_id = "editable-strategy"
        master_profile_path = os.path.join(master_profiles_path, editable_profile_id)
        self._write_profile_file(
            master_profile_path,
            editable_profile_id,
            read_only=False,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
        overlay_profile = profile_storage.get_profile(editable_profile_id)
        profile_storage.delete_profile(editable_profile_id, profile=overlay_profile)
        assert not os.path.isdir(master_profile_path)
        assert not os.path.isdir(os.path.join(child_profiles_path, editable_profile_id))


class TestSyncProfileBackendSaveProfile:
    def test_save_profile_persists_exchanges_and_portfolio(self, tmp_path):
        sync_backend = profile_backends_module.SyncProfileBackend(
            sync_user_id="wallet-user"
        )
        initial_profile_data = profile_data_module.ProfileData.from_dict(
            {
                "profile_details": {"id": "aaaa", "name": "AAAA"},
                "trading": {"reference_market": constants.DEFAULT_REFERENCE_MARKET},
                "trader_simulator": {
                    "enabled": True,
                    "starting_portfolio": {"USDT": 100},
                },
            }
        )
        profile = sync_profile_module.SyncProfile(
            initial_profile_data,
            str(tmp_path / "runtime"),
        )
        profile.profile_id = "aaaa"
        profile.name = "AAAA"
        profile_storage = profile_storage_module.ProfileStorage(
            str(tmp_path / constants.PROFILES_FOLDER),
            None,
            sync_backend=sync_backend,
        )
        profile.bind_profile_storage(profile_storage)
        global_config = {
            constants.CONFIG_CRYPTO_CURRENCIES: copy.deepcopy(
                profile.config[constants.CONFIG_CRYPTO_CURRENCIES]
            ),
            constants.CONFIG_DISTRIBUTION: profile.config[constants.CONFIG_DISTRIBUTION],
            constants.CONFIG_TRADING: copy.deepcopy(profile.config[constants.CONFIG_TRADING]),
            constants.CONFIG_TRADER: copy.deepcopy(profile.config[constants.CONFIG_TRADER]),
            constants.CONFIG_SIMULATOR: {
                constants.CONFIG_ENABLED_OPTION: True,
                constants.CONFIG_STARTING_PORTFOLIO: {"BTC": 5, "USDT": 5000},
                constants.CONFIG_SIMULATOR_FEES: {
                    constants.CONFIG_SIMULATOR_FEES_MAKER: 0.1,
                    constants.CONFIG_SIMULATOR_FEES_TAKER: 0.1,
                },
            },
            constants.CONFIG_EXCHANGES: {
                "binance": {
                    constants.CONFIG_ENABLED_OPTION: True,
                    constants.CONFIG_EXCHANGE_TYPE: "spot",
                },
            },
        }
        strategy_provider = mock.Mock()
        strategy_provider.update_item = mock.Mock()
        with mock.patch.object(
            sync_backend,
            "_get_strategy_provider",
            mock.Mock(return_value=strategy_provider),
        ):
            profile.save_config(global_config)
        saved_profile_data = profile.get_profile_data()
        assert saved_profile_data.trader_simulator.starting_portfolio == {
            "BTC": 5,
            "USDT": 5000,
        }
        assert len(saved_profile_data.exchanges) == 1
        assert saved_profile_data.exchanges[0].internal_name == "binance"
        assert saved_profile_data.exchanges[0].exchange_type == "spot"
        strategy_provider.update_item.assert_called_once()

    def test_save_profile_persists_backtesting_profile_type(self, tmp_path):
        sync_backend = profile_backends_module.SyncProfileBackend(
            sync_user_id="wallet-user"
        )
        initial_profile_data = profile_data_module.ProfileData.from_dict(
            {
                "profile_details": {
                    "id": "backtest-profile",
                    "name": "Backtesting profile",
                    "profile_type": enums.ProfileType.BACKTESTING.value,
                },
                "trading": {"reference_market": constants.DEFAULT_REFERENCE_MARKET},
                "trader_simulator": {
                    "enabled": True,
                    "starting_portfolio": {"USDT": 100},
                },
            }
        )
        profile = sync_profile_module.SyncProfile(
            initial_profile_data,
            str(tmp_path / "runtime"),
        )
        profile.profile_id = "backtest-profile"
        profile.name = "Backtesting profile"
        profile.profile_type = enums.ProfileType.BACKTESTING
        profile_storage = profile_storage_module.ProfileStorage(
            str(tmp_path / constants.PROFILES_FOLDER),
            None,
            sync_backend=sync_backend,
        )
        profile.bind_profile_storage(profile_storage)
        strategy_provider = mock.Mock()
        strategy_provider.update_item = mock.Mock()
        with mock.patch.object(
            sync_backend,
            "_get_strategy_provider",
            mock.Mock(return_value=strategy_provider),
        ):
            profile.validate_and_save_config()
        saved_profile_data = profile.get_profile_data()
        assert saved_profile_data.profile_details.profile_type == enums.ProfileType.BACKTESTING.value
        assert saved_profile_data.profile_details.name == "Backtesting profile"


def _profile_schema_path() -> str:
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "static",
        "profile_schema.json",
    )


def _cloud_like_fetched_profile_data() -> profile_data_module.ProfileData:
    return profile_data_module.ProfileData.from_dict(
        {
            "profile_details": {
                "name": "proud-bear_fetched_config",
                "id": "test-profile-id",
                "bot_id": "test-bot-id",
            },
            "trading": {"reference_market": "USDT"},
            "trader": {"enabled": True},
            "trader_simulator": {"enabled": False},
            "exchanges": [
                {
                    "internal_name": "lbank",
                    "exchange_type": "spot",
                }
            ],
        }
    )


class TestProfileStorageImportProfileDataFunctional:
    def test_import_profile_data_round_trips_full_profile_shape(self, tmp_path, monkeypatch):
        profile_name = "proud-bear_fetched_config"
        original_slug = profile_name
        bot_install_path = str(tmp_path)
        user_folder = tmp_path / constants.USER_FOLDER
        profiles_path = user_folder / constants.PROFILES_FOLDER
        profiles_path.mkdir(parents=True)
        monkeypatch.chdir(bot_install_path)
        profile_schema = os.path.abspath(_profile_schema_path())
        profile_storage = profile_storage_module.ProfileStorage(str(profiles_path), None)
        assert profile_storage.is_sync_available() is False
        profile_data = _cloud_like_fetched_profile_data()
        tentacles_setup_config_mock = mock.Mock()
        tentacles_setup_config_mock.save_config.return_value = True

        with mock.patch(
            "octobot_tentacles_manager.configuration.profile_tentacles_util.build_setup_config_from_profile_data",
            mock.Mock(return_value=tentacles_setup_config_mock),
        ), mock.patch(
            "octobot_tentacles_manager.configuration.profile_tentacles_util.write_specific_configs_to_profile_folder",
            mock.Mock(return_value=False),
        ):
            imported_profile = asyncio.run(
                profile_storage.import_profile_data(
                    profile_data,
                    profile_schema,
                    bot_install_path,
                    name=profile_name,
                )
            )

        profile_folder = profiles_path / profile_name
        profile_config_path = profile_backends_module.FilesystemProfileBackend.config_file_path(
            str(profile_folder)
        )

        assert profile_folder.is_dir()
        assert os.path.isfile(profile_config_path)
        assert not os.path.isfile(
            os.path.join(profile_folder, constants.CONFIG_TENTACLES_FILE)
        )

        on_disk_profile = json_util.read_file(profile_config_path)
        on_disk_metadata = on_disk_profile[constants.CONFIG_PROFILE]
        assert on_disk_metadata[constants.CONFIG_RISK] is not None
        assert on_disk_metadata[constants.CONFIG_COMPLEXITY] is not None
        assert on_disk_metadata[constants.CONFIG_TYPE] is not None
        assert on_disk_metadata[constants.CONFIG_NAME] == profile_name
        assert on_disk_metadata[constants.CONFIG_SLUG] == original_slug
        assert on_disk_metadata[constants.CONFIG_READ_ONLY] is True
        assert on_disk_metadata[constants.CONFIG_IMPORTED] is True
        assert on_disk_metadata[constants.CONFIG_AUTO_UPDATE] is False
        assert on_disk_metadata[constants.CONFIG_RISK] == enums.ProfileRisk.MODERATE.value
        assert on_disk_metadata[constants.CONFIG_COMPLEXITY] == enums.ProfileComplexity.MEDIUM.value
        assert on_disk_metadata[constants.CONFIG_TYPE] == enums.ProfileType.LIVE.value
        assert on_disk_metadata[constants.CONFIG_EXTRA_BACKTESTING_TIME_FRAMES] == [
            profile_data_import_module.IMPORTED_PROFILES_DEFAULT_EXTRA_BACKTESTING_TIMEFRAME
        ]
        assert on_disk_metadata[constants.CONFIG_ID]

        on_disk_config = on_disk_profile[constants.PROFILE_CONFIG]
        assert on_disk_config[constants.CONFIG_EXCHANGES]["lbank"][constants.CONFIG_ENABLED_OPTION] is True
        assert on_disk_config[constants.CONFIG_TRADER][constants.CONFIG_ENABLED_OPTION] is True
        assert on_disk_config[constants.CONFIG_SIMULATOR][constants.CONFIG_ENABLED_OPTION] is False
        assert (
            on_disk_config[constants.CONFIG_TRADING][constants.CONFIG_TRADER_REFERENCE_MARKET]
            == "USDT"
        )

        self._assert_imported_profile_metadata(
            imported_profile,
            profile_name=profile_name,
            original_slug=original_slug,
        )

        reloaded_profile = profile_backends_module.FilesystemProfileBackend().read_profile_from_path(
            str(profile_folder),
            schema_path=profile_schema,
        )
        self._assert_imported_profile_metadata(
            reloaded_profile,
            profile_name=profile_name,
            original_slug=original_slug,
        )
        assert imported_profile.as_dict()[constants.CONFIG_PROFILE] == reloaded_profile.as_dict()[
            constants.CONFIG_PROFILE
        ]
        assert imported_profile.as_dict()[constants.PROFILE_CONFIG] == reloaded_profile.as_dict()[
            constants.PROFILE_CONFIG
        ]

    def _assert_imported_profile_metadata(
        self,
        profile: profile_module.Profile,
        *,
        profile_name: str,
        original_slug: str,
    ):
        assert profile.name == profile_name
        assert profile.slug == original_slug
        assert profile.read_only is True
        assert profile.imported is True
        assert profile.auto_update is False
        assert profile.risk == enums.ProfileRisk.MODERATE
        assert profile.complexity == enums.ProfileComplexity.MEDIUM
        assert profile.profile_type == enums.ProfileType.LIVE
        assert profile.extra_backtesting_time_frames == [
            profile_data_import_module.IMPORTED_PROFILES_DEFAULT_EXTRA_BACKTESTING_TIMEFRAME
        ]
        assert profile.profile_id
