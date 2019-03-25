#  Drakkar-Software OctoBot
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

from config.config import load_config
from config import CONFIG_EVALUATOR, CONFIG_TRADING_TENTACLES, TimeFrames, CONFIG_TIME_FRAME


TEST_CONFIG_FOLDER = "tests/static"


def init_config_time_frame_for_tests(config):
    result = []
    for time_frame in config[CONFIG_TIME_FRAME]:
        result.append(TimeFrames(time_frame))
    config[CONFIG_TIME_FRAME] = result


def load_test_config():
    config = load_config(f"{TEST_CONFIG_FOLDER}/config.json")
    config[CONFIG_EVALUATOR] = load_config(f"{TEST_CONFIG_FOLDER}/evaluator_config.json", False)
    config[CONFIG_TRADING_TENTACLES] = load_config(f"{TEST_CONFIG_FOLDER}/trading_config.json", False)
    init_config_time_frame_for_tests(config)
    return config
