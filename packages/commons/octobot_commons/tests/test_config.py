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

import octobot_commons.configuration as configuration
import octobot_commons.constants as constants
import octobot_commons.enums as enums

TEST_FOLDER = "tests"
STATIC_FOLDER = "static"
TEST_CONFIG_FOLDER = f"{TEST_FOLDER}/static"


def get_test_config(test_folder=TEST_FOLDER):
    """
    Return test default config
    :return: test default config
    """
    return os.path.join(test_folder, STATIC_FOLDER, constants.CONFIG_FILE)


def get_test_profile(test_folder=TEST_FOLDER):
    """
    Return test default config
    :return: test default config
    """
    return test_folder


def init_config_time_frame_for_tests(config):
    """
    Append time frames to config for tests
    :param config: the test config
    :return: the test config with time frames
    """
    result = []
    for time_frame in config[constants.CONFIG_TIME_FRAME]:
        result.append(enums.TimeFrames(time_frame))
    config[constants.CONFIG_TIME_FRAME] = result


def load_test_config(dict_only=True, test_folder=TEST_FOLDER):
    """
    Return the complete default test configs
    :return: the complete default test config
    """
    config = configuration.Configuration(
        get_test_config(test_folder=test_folder),
        get_test_profile(test_folder=test_folder),
    )
    config.read()
    init_config_time_frame_for_tests(config.config)
    return config.config if dict_only else config
