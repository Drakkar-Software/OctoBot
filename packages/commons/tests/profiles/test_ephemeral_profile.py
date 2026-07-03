#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest

import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.profiles.profile_types.ephemeral_profile as ephemeral_profile_module
import octobot_commons.profiles.profile_data as profile_data_module


class TestEphemeralProfileFromProfileData:
    def test_from_profile_data_returns_ephemeral_profile(self):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        assert isinstance(profile, ephemeral_profile_module.EphemeralProfile)
        assert profile.path is None
        assert profile.get_storage_source() == enums.ProfileSource.EPHEMERAL
        assert profile.is_profile_data_tentacle_backed() is True
        assert profile.is_sync_backed() is False


class TestEphemeralProfileInitTentaclesSetupConfig:
    def test_init_tentacles_setup_config_does_not_require_filesystem_path(self):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        profile.init_tentacles_setup_config()
        assert profile.tentacles_setup_config is not None


class TestEphemeralProfileBindTentaclesSetupConfig:
    def test_sets_both_profile_and_setup_references(self):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        setup = mock.Mock()
        returned_setup = profile.bind_tentacles_setup_config(setup)
        assert returned_setup is setup
        assert setup.profile is profile
        assert profile.tentacles_setup_config is setup


class TestEphemeralProfileGetTentaclesConfigPath:
    def test_raises_profile_data_error(self):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        with pytest.raises(errors.ProfileDataError):
            profile.get_tentacles_config_path()


class TestEphemeralProfileSave:
    def test_save_raises_profile_data_error(self):
        profile_data = profile_data_module.ProfileData()
        profile = ephemeral_profile_module.EphemeralProfile.from_profile_data(profile_data)
        with pytest.raises(errors.ProfileDataError):
            profile.save()
