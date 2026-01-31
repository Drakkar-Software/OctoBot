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
import os

import pytest
import pathlib
import octobot_commons.profiles as profiles
import octobot_commons.tests.test_config as test_config


def get_profile_path():
    return test_config.TEST_CONFIG_FOLDER


def get_profiles_path():
    return pathlib.Path(get_profile_path()).parent


@pytest.fixture
def profile():
    return profiles.Profile(get_profile_path())


@pytest.fixture
def invalid_profile():
    return profiles.Profile(os.path.join(get_profile_path(), "invalid_profile"))
