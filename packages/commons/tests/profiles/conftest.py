#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import os

import pytest
import pathlib

import octobot_commons.constants as constants
import octobot_commons.profiles as profiles
import octobot_commons.profiles.backends as profile_backends_module
import octobot_commons.profiles.profile_storage as profile_storage_module
import octobot_commons.tests.test_config as test_config
import octobot_commons.user_root_folder_provider as user_root_folder_provider

PROFILES_FS_XDIST_GROUP = "profiles_fs"


def get_profile_path():
    return test_config.TEST_CONFIG_FOLDER


def get_profiles_path():
    return pathlib.Path(get_profile_path()).parent


@pytest.fixture
def profile_storage(tmp_path):
    profiles_path = tmp_path / constants.PROFILES_FOLDER
    profiles_path.mkdir()
    storage = profile_storage_module.ProfileStorage(str(profiles_path), None)
    yield storage


@pytest.fixture
def profile_storage_for_tests():
    return profile_storage_module.ProfileStorage(str(get_profiles_path()), None)


@pytest.fixture
def profile(profile_storage_for_tests):
    filesystem_backend = profile_backends_module.FilesystemProfileBackend()
    loaded_profile = filesystem_backend.read_profile_from_path(get_profile_path())
    loaded_profile.bind_profile_storage(profile_storage_for_tests)
    return loaded_profile


@pytest.fixture
def invalid_profile():
    return profiles.Profile(os.path.join(get_profile_path(), "invalid_profile"))


@pytest.fixture
def reset_user_root_folder_provider():
    provider = user_root_folder_provider.UserRootFolderProvider.instance()
    previous_root = provider._root
    previous_readonly_reference = provider._readonly_reference_tentacles_path
    provider.set_root(None)
    provider.configure_readonly_reference_tentacles_path("")
    yield
    provider.set_root(previous_root)
    provider.configure_readonly_reference_tentacles_path(previous_readonly_reference or "")
