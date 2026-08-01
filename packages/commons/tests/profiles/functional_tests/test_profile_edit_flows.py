#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import os

import pytest

import octobot_commons.constants as constants
import octobot_commons.errors as errors_module
import octobot_commons.json_util as json_util
import octobot_commons.profiles.profile_data as profile_data_module
import octobot_commons.profiles.profile_storage as profile_storage_module
import octobot_commons.profiles.profile_types.ephemeral_profile as ephemeral_profile_module
import octobot_commons.profiles.profile_types.sync_profile as sync_profile_module
import octobot_tentacles_manager.configuration.tentacle_configuration as tentacle_configuration
import octobot_tentacles_manager.constants as tentacles_constants

TENTACLE_NAME = "DailyTradingMode"
DEFAULT_ACTIVATION = {"Trading": {TENTACLE_NAME: True}}


def _write_profile_file(profile_path: str, profile_id: str, *, read_only: bool) -> None:
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


def _write_tentacles_config(profile_folder: str, activation_dict: dict) -> str:
    os.makedirs(profile_folder, exist_ok=True)
    tentacles_config_path = os.path.join(profile_folder, constants.CONFIG_TENTACLES_FILE)
    json_util.safe_dump(
        {
            "tentacle_activation": activation_dict,
            "registered_tentacles": {},
            "installation_context": {},
        },
        tentacles_config_path,
    )
    return tentacles_config_path


def _read_json(file_path: str) -> dict:
    return json_util.read_file(file_path)


def _master_child_storage(tmp_path, profile_id: str, *, read_only: bool):
    child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
    child_profiles_path.mkdir(parents=True)
    master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
    master_profile_path = os.path.join(master_profiles_path, profile_id)
    _write_profile_file(master_profile_path, profile_id, read_only=read_only)
    profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
    profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
    return profile_storage, str(master_profiles_path), str(child_profiles_path), master_profile_path


def _local_storage(tmp_path, profile_id: str, *, read_only: bool):
    child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
    profile_path = os.path.join(child_profiles_path, profile_id)
    _write_profile_file(profile_path, profile_id, read_only=read_only)
    profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
    return profile_storage, str(child_profiles_path), profile_path


def _minimal_tentacle_klass(tentacle_name: str):
    return type(
        tentacle_name,
        (),
        {"get_name": staticmethod(lambda: tentacle_name)},
    )()


def _seed_empty_specific_config(writable_profile_path: str, tentacle_name: str) -> str:
    specific_config_dir = os.path.join(
        writable_profile_path,
        constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
    )
    os.makedirs(specific_config_dir, exist_ok=True)
    specific_config_path = os.path.join(
        specific_config_dir,
        f"{tentacle_name}{tentacles_constants.CONFIG_EXT}",
    )
    if not os.path.isfile(specific_config_path):
        json_util.safe_dump({}, specific_config_path)
    return specific_config_path


def _trader_enabled(profile_json: dict) -> bool:
    return profile_json[constants.PROFILE_CONFIG][constants.CONFIG_TRADER][
        constants.CONFIG_ENABLED_OPTION
    ]


def _assert_trader_enabled(profile_json: dict) -> None:
    assert _trader_enabled(profile_json) is True


def _assert_trader_disabled(profile_json: dict) -> None:
    assert _trader_enabled(profile_json) is False


def _assert_activation_unchanged(before: dict, after: dict) -> None:
    assert before == after


def _save_trader_enabled(profile, profile_storage: profile_storage_module.ProfileStorage) -> None:
    profile.config[constants.CONFIG_TRADER] = {constants.CONFIG_ENABLED_OPTION: True}
    profile_storage.save_active_profile(profile, {})


class TestMasterOverlayReadonlyProfileEditFlow:
    def test_full_edit_flow(self, tmp_path):
        """Allowed: profile config (child overlay), tentacle config (child writable path).
        Not allowed: tentacle activation (master tentacles_config.json unchanged)."""
        profile_id = "readonly-strategy"
        profile_storage, master_profiles_path, child_profiles_path, master_profile_path = (
            _master_child_storage(tmp_path, profile_id, read_only=True)
        )
        master_tentacles_path = _write_tentacles_config(master_profile_path, DEFAULT_ACTIVATION)
        tentacles_before = _read_json(master_tentacles_path)

        # Activate: tentacles setup reads activation from master path.
        profile = profile_storage.get_profile(profile_id)
        profile_storage.activate_profile(profile)
        setup = profile.tentacles_setup_config

        # Profile config: allowed; persists to child overlay only.
        _save_trader_enabled(profile, profile_storage)
        child_overlay_file = _read_json(
            os.path.join(child_profiles_path, profile_id, constants.PROFILE_CONFIG_FILE)
        )
        master_profile_file = _read_json(
            os.path.join(master_profile_path, constants.PROFILE_CONFIG_FILE)
        )
        _assert_trader_enabled(child_overlay_file)
        _assert_trader_disabled(master_profile_file)

        # Tentacle config: allowed; specific_config under child writable path.
        writable_path = profile.get_writable_profile_path()
        _seed_empty_specific_config(writable_path, TENTACLE_NAME)
        tentacle_klass = _minimal_tentacle_klass(TENTACLE_NAME)
        tentacle_configuration.update_config(
            setup, tentacle_klass, {"amount": 1}, keep_existing=False
        )
        child_specific_config_path = os.path.join(
            writable_path,
            constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
            f"{TENTACLE_NAME}{tentacles_constants.CONFIG_EXT}",
        )
        assert os.path.isfile(child_specific_config_path)
        assert _read_json(child_specific_config_path) == {"amount": 1}
        assert not os.path.isdir(
            os.path.join(master_profile_path, constants.TENTACLES_SPECIFIC_CONFIG_FOLDER)
        )

        # Tentacle activation: blocked; master tentacles_config.json unchanged.
        with pytest.raises(errors_module.ProfileDataError, match="strategy is read-only"):
            setup.save_config(is_config_update=False)
        _assert_activation_unchanged(tentacles_before, _read_json(master_tentacles_path))

        # Re-activation: child overlay config still merged in memory.
        profile_storage.activate_profile(profile)
        assert profile.config[constants.CONFIG_TRADER][constants.CONFIG_ENABLED_OPTION] is True


class TestLocalReadonlyProfileEditFlow:
    def test_full_edit_flow(self, tmp_path):
        """Allowed: profile config, tentacle config (local profile path).
        Not allowed: tentacle activation."""
        profile_id = "local-readonly"
        profile_storage, child_profiles_path, profile_path = _local_storage(
            tmp_path, profile_id, read_only=True
        )
        tentacles_path = _write_tentacles_config(profile_path, DEFAULT_ACTIVATION)
        tentacles_before = _read_json(tentacles_path)

        profile = profile_storage.get_profile(profile_id)
        profile_storage.activate_profile(profile)
        setup = profile.tentacles_setup_config

        # Profile config: allowed on standard filesystem path.
        _save_trader_enabled(profile, profile_storage)
        profile_file = _read_json(os.path.join(profile_path, constants.PROFILE_CONFIG_FILE))
        _assert_trader_enabled(profile_file)

        # Tentacle config: allowed under profile.path/specific_config/.
        _seed_empty_specific_config(profile_path, TENTACLE_NAME)
        tentacle_klass = _minimal_tentacle_klass(TENTACLE_NAME)
        tentacle_configuration.update_config(
            setup, tentacle_klass, {"amount": 1}, keep_existing=False
        )
        specific_config_path = os.path.join(
            profile_path,
            constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
            f"{TENTACLE_NAME}{tentacles_constants.CONFIG_EXT}",
        )
        assert _read_json(specific_config_path) == {"amount": 1}

        # Tentacle activation: blocked on read-only local profile.
        with pytest.raises(errors_module.ProfileDataError, match="strategy is read-only"):
            setup.save_config(is_config_update=False)
        _assert_activation_unchanged(tentacles_before, _read_json(tentacles_path))


class TestEditableLocalProfileEditFlow:
    def test_full_edit_flow(self, tmp_path):
        """Allowed: profile config, tentacle config, tentacle activation (all on local path)."""
        profile_id = "editable-local"
        profile_storage, _child_profiles_path, profile_path = _local_storage(
            tmp_path, profile_id, read_only=False
        )
        tentacles_path = _write_tentacles_config(profile_path, DEFAULT_ACTIVATION)

        profile = profile_storage.get_profile(profile_id)
        profile_storage.activate_profile(profile)
        setup = profile.tentacles_setup_config

        # Profile config: persists to profile.path/profile.json.
        _save_trader_enabled(profile, profile_storage)
        _assert_trader_enabled(_read_json(os.path.join(profile_path, constants.PROFILE_CONFIG_FILE)))

        # Tentacle config: persists to specific_config/.
        _seed_empty_specific_config(profile_path, TENTACLE_NAME)
        tentacle_klass = _minimal_tentacle_klass(TENTACLE_NAME)
        tentacle_configuration.update_config(
            setup, tentacle_klass, {"amount": 1}, keep_existing=False
        )
        specific_config_path = os.path.join(
            profile_path,
            constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
            f"{TENTACLE_NAME}{tentacles_constants.CONFIG_EXT}",
        )
        assert _read_json(specific_config_path) == {"amount": 1}

        # Tentacle activation: allowed; writes tentacles_config.json on disk.
        setup.tentacles_activation["Trading"][TENTACLE_NAME] = False
        assert setup.save_config(is_config_update=False) is True
        tentacles_after = _read_json(tentacles_path)
        assert tentacles_after["tentacle_activation"]["Trading"][TENTACLE_NAME] is False


class TestEditableMasterOverlayProfileEditFlow:
    def test_full_edit_flow(self, tmp_path):
        """Allowed: profile config, tentacle config, tentacle activation (all on master path)."""
        profile_id = "editable-strategy"
        profile_storage, _master_profiles_path, child_profiles_path, master_profile_path = (
            _master_child_storage(tmp_path, profile_id, read_only=False)
        )
        tentacles_path = _write_tentacles_config(master_profile_path, DEFAULT_ACTIVATION)

        profile = profile_storage.get_profile(profile_id)
        profile_storage.activate_profile(profile)
        setup = profile.tentacles_setup_config

        # Profile config: persists to master path; no child overlay directory.
        _save_trader_enabled(profile, profile_storage)
        _assert_trader_enabled(_read_json(os.path.join(master_profile_path, constants.PROFILE_CONFIG_FILE)))
        assert not os.path.isdir(os.path.join(child_profiles_path, profile_id))

        # Tentacle config: persists to master specific_config/.
        _seed_empty_specific_config(master_profile_path, TENTACLE_NAME)
        tentacle_klass = _minimal_tentacle_klass(TENTACLE_NAME)
        tentacle_configuration.update_config(
            setup, tentacle_klass, {"amount": 1}, keep_existing=False
        )
        master_specific_config_path = os.path.join(
            master_profile_path,
            constants.TENTACLES_SPECIFIC_CONFIG_FOLDER,
            f"{TENTACLE_NAME}{tentacles_constants.CONFIG_EXT}",
        )
        assert _read_json(master_specific_config_path) == {"amount": 1}

        # Tentacle activation: allowed; writes master tentacles_config.json.
        setup.tentacles_activation["Trading"][TENTACLE_NAME] = False
        assert setup.save_config(is_config_update=False) is True
        assert _read_json(tentacles_path)["tentacle_activation"]["Trading"][TENTACLE_NAME] is False


class TestEphemeralProfileEditFlow:
    def test_full_edit_flow(self, tmp_path):
        """Allowed: tentacle config (ProfileData RAM only).
        Not allowed: profile config persistence, tentacle activation persistence."""
        profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        profiles_path.mkdir(parents=True)
        profile_storage = profile_storage_module.ProfileStorage(str(profiles_path), None)
        profile_data = profile_data_module.ProfileData()
        profile_data.profile_details.id = "ephemeral-strategy"
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        profile_storage.activate_profile(profile)
        setup = profile.tentacles_setup_config

        # Profile config: ephemeral profiles cannot be persisted.
        profile.config[constants.CONFIG_TRADER] = {constants.CONFIG_ENABLED_OPTION: True}
        with pytest.raises(errors_module.ProfileDataError, match="Ephemeral profiles cannot be persisted"):
            profile_storage.save_active_profile(profile, {})

        # Tentacle config: stored in ProfileData RAM only.
        tentacle_klass = _minimal_tentacle_klass(TENTACLE_NAME)
        tentacle_configuration.update_config(
            setup, tentacle_klass, {"amount": 1}, keep_existing=False
        )
        assert profile_data.tentacles[0].name == TENTACLE_NAME
        assert profile_data.tentacles[0].config == {"amount": 1}

        # Tentacle activation: blocked for ephemeral storage source.
        setup.tentacles_activation = dict(DEFAULT_ACTIVATION)
        with pytest.raises(errors_module.ProfileDataError, match="Ephemeral profiles cannot be persisted"):
            setup.save_config(is_config_update=False)


class TestSyncProfileReadonlyEditFlow:
    def test_full_edit_flow(self, tmp_path):
        """Allowed: tentacle config (ProfileData RAM), tentacle activation (in-memory; sync read-only exempt)."""
        profile_id = "sync-readonly"
        runtime_path = tmp_path / "runtime" / profile_id
        runtime_path.mkdir(parents=True)
        profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        profiles_path.mkdir(parents=True)
        profile_data = profile_data_module.ProfileData()
        profile_data.profile_details.id = profile_id
        profile = sync_profile_module.SyncProfile(profile_data, str(runtime_path))
        profile.read_only = True
        profile_storage = profile_storage_module.ProfileStorage(str(profiles_path), None)
        profile_storage.activate_profile(profile)
        setup = profile.tentacles_setup_config
        setup.tentacles_activation = dict(DEFAULT_ACTIVATION)

        # Tentacle config: stored in ProfileData RAM.
        tentacle_klass = _minimal_tentacle_klass(TENTACLE_NAME)
        tentacle_configuration.update_config(
            setup, tentacle_klass, {"amount": 2}, keep_existing=False
        )
        assert profile_data.tentacles[0].name == TENTACLE_NAME
        assert profile_data.tentacles[0].config == {"amount": 2}

        # Tentacle activation: allowed for sync read_only (gate exempts sync-backed profiles).
        setup.tentacles_activation["Trading"][TENTACLE_NAME] = False
        assert setup.save_config(is_config_update=False) is True
        assert setup.tentacles_activation["Trading"][TENTACLE_NAME] is False
