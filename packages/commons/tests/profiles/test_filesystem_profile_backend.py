#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import json
import os

import mock
import pytest

import octobot_commons.constants as constants
import octobot_commons.errors as errors
import octobot_commons.json_util as json_util
import octobot_commons.profiles.backends as profile_backends_module
import octobot_commons.tests.test_config as test_config

import tests.profiles.conftest as profiles_conftest
from tests.profiles import get_profile_path, get_profiles_path


class TestFilesystemProfileBackendReadWrite:
    def test_read_profile_from_path(self):
        filesystem_backend = profile_backends_module.FilesystemProfileBackend()
        profile = filesystem_backend.read_profile_from_path(get_profile_path())
        assert profile.profile_id == "default"
        assert profile.name == "default"
        assert profile.description == "OctoBot default profile."
        assert profile.avatar == "default_profile.png"
        assert profile.avatar_path == os.path.join(
            test_config.TEST_CONFIG_FOLDER, "default_profile.png"
        )
        assert profile.origin_url == "https://default.url"
        assert profile.config[constants.CONFIG_DISTRIBUTION] == constants.DEFAULT_DISTRIBUTION
        assert len(profile.config) == 6

    def test_read_profile_from_path_raises_when_missing(self):
        filesystem_backend = profile_backends_module.FilesystemProfileBackend()
        with pytest.raises(errors.ProfileDataError):
            filesystem_backend.read_profile_from_path("")

    def test_write_profile_config(self):
        filesystem_backend = profile_backends_module.FilesystemProfileBackend()
        profile = filesystem_backend.read_profile_from_path(get_profile_path())
        save_file = "profile_config.json"
        if os.path.isfile(save_file):
            os.remove(save_file)
        try:
            profile.config = {"a": 1}
            with mock.patch.object(
                filesystem_backend,
                "config_file_path",
                mock.Mock(return_value=save_file),
            ):
                filesystem_backend.write_profile_config(profile)
            with open(save_file) as config_file:
                saved_profile = json.load(config_file)
            assert saved_profile == profile.as_dict()
        finally:
            if os.path.isfile(save_file):
                os.remove(save_file)

    def test_config_file_path(self):
        assert profile_backends_module.FilesystemProfileBackend.config_file_path(
            get_profile_path()
        ) == os.path.join(get_profile_path(), constants.PROFILE_CONFIG_FILE)


class TestFilesystemProfileBackendDiscovery:
    def test_scan_profiles(self):
        filesystem_backend = profile_backends_module.FilesystemProfileBackend()
        with mock.patch.object(
            filesystem_backend,
            "_load_profile_from_folder",
            mock.Mock(),
        ) as load_profile_mock:
            nb_files = len(os.listdir(get_profiles_path()))
            assert nb_files > 1
            filesystem_backend._scan_profiles(str(get_profiles_path()))
            assert load_profile_mock.call_count == nb_files

    def test_load_profile_from_folder(self):
        schema_path = "schema_path"
        filesystem_backend = profile_backends_module.FilesystemProfileBackend()
        with mock.patch.object(
            json_util,
            "read_file",
            mock.Mock(return_value={
                constants.CONFIG_PROFILE: {},
                constants.PROFILE_CONFIG: {},
            }),
        ) as read_file_mock:
            profile = filesystem_backend._load_profile_from_folder(
                test_config.TEST_CONFIG_FOLDER, schema_path
            )
            assert profile.path == test_config.TEST_CONFIG_FOLDER
            assert profile.schema_path == schema_path
            read_file_mock.assert_called_once()

    def test_load_profile(self):
        profiles_path = str(get_profiles_path())
        filesystem_backend = profile_backends_module.FilesystemProfileBackend(
            profiles_path, None
        )
        profile = filesystem_backend.load_profile("default")
        assert profile.profile_id == "default"

    @pytest.mark.xdist_group(name=profiles_conftest.PROFILES_FS_XDIST_GROUP)
    def test_list_profile_ids(self, profile):
        profiles_path = str(get_profiles_path())
        filesystem_backend = profile_backends_module.FilesystemProfileBackend(
            profiles_path, None
        )
        assert filesystem_backend.list_profile_ids() == ["default"]
        assert filesystem_backend.list_profile_ids(ignore=profile.path) == []


class TestFilesystemProfileBackendMutations:
    def test_duplicate_profile_raises_not_implemented(self, profile):
        filesystem_backend = profile_backends_module.FilesystemProfileBackend(
            str(get_profiles_path()), None
        )
        with pytest.raises(NotImplementedError):
            filesystem_backend.duplicate_profile(profile)
