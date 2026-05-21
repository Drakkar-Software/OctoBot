#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pathlib
import shutil

import pytest

import tests.profiles as profiles_tests

PROFILES_FS_XDIST_GROUP = "profiles_fs"

_EPHEMERAL_PROFILE_DIRECTORIES = (
    "second_profile",
    "other_profile",
)


@pytest.fixture(autouse=True)
def _clean_ephemeral_test_profile_directories():
    profiles_path = pathlib.Path(profiles_tests.get_profiles_path())
    for directory_name in _EPHEMERAL_PROFILE_DIRECTORIES:
        directory_path = profiles_path.joinpath(directory_name)
        if directory_path.is_dir():
            shutil.rmtree(directory_path)
    yield
    for directory_name in _EPHEMERAL_PROFILE_DIRECTORIES:
        directory_path = profiles_path.joinpath(directory_name)
        if directory_path.is_dir():
            shutil.rmtree(directory_path)
