#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import logging
import os

import pytest

import octobot_commons.constants as constants
import octobot_commons.errors as errors_module
import octobot_commons.json_util as json_util
import octobot_commons.profiles.profile_edit_gate as profile_edit_gate_module
import octobot_commons.profiles.profile_storage as profile_storage_module


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


def _master_child_storage(tmp_path, readonly_profile_id: str, *, read_only: bool):
    child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
    child_profiles_path.mkdir(parents=True)
    master_profiles_path = tmp_path / "master" / constants.PROFILES_FOLDER
    _write_profile_file(
        os.path.join(master_profiles_path, readonly_profile_id),
        readonly_profile_id,
        read_only=read_only,
    )
    profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
    profile_storage.configure_readonly_profiles_path(str(master_profiles_path))
    return profile_storage, str(master_profiles_path), str(child_profiles_path)


class TestProfileEditGateAssertEditAllowed:
    def test_blocks_tentacle_activation_on_read_only_profile(self, tmp_path, caplog):
        profile_storage, _, _ = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        edit_gate = profile_storage.edit_gate
        with pytest.raises(errors_module.ProfileDataError, match="strategy is read-only"):
            edit_gate.assert_edit_allowed(
                profile,
                profile_edit_gate_module.ProfileEditType.TENTACLE_ACTIVATION,
            )
        assert any(
            record.levelname == "ERROR" and "Blocked profile edit" in record.message
            for record in caplog.records
        )

    def test_allows_profile_config_on_read_only_overlay(self, tmp_path):
        profile_storage, _, _ = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        profile_storage.edit_gate.assert_edit_allowed(
            profile,
            profile_edit_gate_module.ProfileEditType.PROFILE_CONFIG,
        )

    def test_allows_tentacle_config_on_read_only_overlay(self, tmp_path):
        profile_storage, _, _ = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        profile_storage.edit_gate.assert_edit_allowed(
            profile,
            profile_edit_gate_module.ProfileEditType.TENTACLE_CONFIG,
        )

    def test_allows_tentacle_activation_on_editable_profile(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        profile_id = "editable-local"
        _write_profile_file(
            os.path.join(child_profiles_path, profile_id),
            profile_id,
            read_only=False,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile = profile_storage.get_profile(profile_id)
        profile_storage.edit_gate.assert_edit_allowed(
            profile,
            profile_edit_gate_module.ProfileEditType.TENTACLE_ACTIVATION,
        )


class TestProfileEditGateResolveWritablePath:
    def test_read_only_overlay_uses_child_path(self, tmp_path):
        profile_storage, _, child_profiles_path = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        writable_path = profile_storage.edit_gate.resolve_writable_path(
            profile,
            profile_edit_gate_module.ProfileEditType.PROFILE_CONFIG,
        )
        assert writable_path == os.path.join(child_profiles_path, "readonly-strategy")

    def test_local_profile_uses_profile_path(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        profile_id = "local-profile"
        profile_path = os.path.join(child_profiles_path, profile_id)
        _write_profile_file(profile_path, profile_id, read_only=True)
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile = profile_storage.get_profile(profile_id)
        writable_path = profile_storage.edit_gate.resolve_writable_path(
            profile,
            profile_edit_gate_module.ProfileEditType.TENTACLE_CONFIG,
        )
        assert writable_path == profile_path

    def test_editable_master_overlay_uses_master_path(self, tmp_path):
        profile_storage, master_profiles_path, _ = _master_child_storage(
            tmp_path, "editable-strategy", read_only=False
        )
        profile = profile_storage.get_profile("editable-strategy")
        writable_path = profile_storage.edit_gate.resolve_writable_path(
            profile,
            profile_edit_gate_module.ProfileEditType.PROFILE_CONFIG,
        )
        assert writable_path == os.path.join(master_profiles_path, "editable-strategy")


class TestProfileEditGateResolveActivationReadPath:
    def test_read_only_overlay_reads_master_tentacles_config(self, tmp_path):
        profile_storage, master_profiles_path, _ = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        activation_path = profile_storage.edit_gate.resolve_activation_read_path(profile)
        assert activation_path == os.path.join(
            master_profiles_path,
            "readonly-strategy",
            constants.CONFIG_TENTACLES_FILE,
        )


class TestProfileEditGateResolvePersistenceTarget:
    def test_read_only_overlay_is_child_override(self, tmp_path):
        profile_storage, _, _ = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        target = profile_storage.edit_gate.resolve_persistence_target(
            profile,
            profile_edit_gate_module.ProfileEditType.PROFILE_CONFIG,
        )
        assert target is profile_edit_gate_module.ProfilePersistenceTarget.CHILD_OVERRIDE

    def test_local_profile_is_standard_filesystem(self, tmp_path):
        child_profiles_path = tmp_path / "child" / constants.PROFILES_FOLDER
        profile_id = "local-profile"
        _write_profile_file(
            os.path.join(child_profiles_path, profile_id),
            profile_id,
            read_only=True,
        )
        profile_storage = profile_storage_module.ProfileStorage(str(child_profiles_path), None)
        profile = profile_storage.get_profile(profile_id)
        target = profile_storage.edit_gate.resolve_persistence_target(
            profile,
            profile_edit_gate_module.ProfileEditType.PROFILE_CONFIG,
        )
        assert target is profile_edit_gate_module.ProfilePersistenceTarget.STANDARD_FILESYSTEM

    def test_editable_master_overlay_is_master_overlay(self, tmp_path):
        profile_storage, _, _ = _master_child_storage(
            tmp_path, "editable-strategy", read_only=False
        )
        profile = profile_storage.get_profile("editable-strategy")
        target = profile_storage.edit_gate.resolve_persistence_target(
            profile,
            profile_edit_gate_module.ProfileEditType.PROFILE_CONFIG,
        )
        assert target is profile_edit_gate_module.ProfilePersistenceTarget.MASTER_OVERLAY


class TestProfileEditGateLogEditSaved:
    def test_logs_info_with_edit_type_and_persistence_target(self, tmp_path, caplog):
        profile_storage, _, _ = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        with caplog.at_level(logging.INFO, logger="ProfileEdit"):
            profile_storage.edit_gate.log_edit_saved(
                profile,
                profile_edit_gate_module.ProfileEditType.PROFILE_CONFIG,
                "/tmp/child/profile.json",
            )
        assert any(
            record.levelname == "INFO"
            and "edit_type=profile_config" in record.getMessage()
            and "persistence_target=child_override" in record.getMessage()
            for record in caplog.records
        )


class TestProfileEditGateLogEditBlocked:
    def test_logs_error_with_reason(self, tmp_path, caplog):
        profile_storage, _, _ = _master_child_storage(
            tmp_path, "readonly-strategy", read_only=True
        )
        profile = profile_storage.get_profile("readonly-strategy")
        profile_storage.edit_gate.log_edit_blocked(
            profile,
            profile_edit_gate_module.ProfileEditType.TENTACLE_ACTIVATION,
            "blocked for test",
        )
        assert any(
            record.levelname == "ERROR"
            and "Blocked profile edit" in record.message
            and "blocked for test" in record.message
            for record in caplog.records
        )
