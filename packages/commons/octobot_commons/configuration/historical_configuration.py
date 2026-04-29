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
import octobot_commons.constants as constants


def add_historical_tentacle_config(
    master_config: dict, config_start_time: float, historical_config: dict
):
    """
    Adds the given historical_config to the master_config historical configurations
    """
    if constants.CONFIG_HISTORICAL_CONFIGURATION not in master_config:
        master_config[constants.CONFIG_HISTORICAL_CONFIGURATION] = []
    # use list to ensure it still can be serialized
    master_config[constants.CONFIG_HISTORICAL_CONFIGURATION].append(
        [config_start_time, historical_config]
    )
    # always keep the most recent first to be able to find the most up to date first when iterating
    master_config[constants.CONFIG_HISTORICAL_CONFIGURATION].sort(
        key=lambda x: x[0], reverse=True
    )


def has_any_historical_tentacle_config(master_config: dict) -> bool:
    """
    :return: True if there is any historical configuration in the master_config
    """
    return constants.CONFIG_HISTORICAL_CONFIGURATION in master_config


def get_historical_tentacle_config(master_config: dict, current_time: float) -> dict:
    """
    :return: the historical configuration associated to the given time
    """
    try:
        for config_start_time_and_config in master_config[
            constants.CONFIG_HISTORICAL_CONFIGURATION
        ]:
            if config_start_time_and_config[0] <= current_time:
                return config_start_time_and_config[1]
        # no suitable config found: fallback to the oldest config
        return master_config[constants.CONFIG_HISTORICAL_CONFIGURATION][-1][1]
    except KeyError:
        raise KeyError(
            f"{constants.CONFIG_HISTORICAL_CONFIGURATION} not found in master_config."
        )


def get_historical_tentacle_configs(
    master_config: dict, from_time: float, to_time: float
) -> list[dict]:
    """
    :return: the historical configurations corresponding to the given time interval,
    ordered by the most recent config first
    """
    try:
        return [
            config_start_time_and_config[1]
            for config_start_time_and_config in master_config[
                constants.CONFIG_HISTORICAL_CONFIGURATION
            ]
            if (
                config_start_time_and_config[0] >= from_time
                and config_start_time_and_config[0] <= to_time
            )
        ]
    except KeyError:
        raise KeyError(
            f"{constants.CONFIG_HISTORICAL_CONFIGURATION} not found in master_config."
        )


def get_oldest_historical_tentacle_config_time(master_config: dict) -> float:
    """
    :return: the oldest historical configuration timestamp
    """
    try:
        return min(
            historical_config[0]
            for historical_config in master_config.get(
                constants.CONFIG_HISTORICAL_CONFIGURATION, []
            )
        )
    except ValueError:
        raise ValueError("No historical configuration found")
