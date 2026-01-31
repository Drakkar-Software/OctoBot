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
import octobot_commons.constants as constants
import octobot_commons.logging as logging_util
import octobot_commons.enums as enums

LOGGER_TAG = "TimeFrameManager"


def _sort_time_frames(time_frames, reverse=False):
    if time_frames:
        time_frames = (
            time_frames
            if isinstance(time_frames[0], enums.TimeFrames)
            else [enums.TimeFrames(tf) for tf in time_frames]
        )
        return sorted(
            time_frames, key=enums.TimeFramesMinutes.__getitem__, reverse=reverse
        )
    return time_frames


TimeFramesRank = _sort_time_frames(list(enums.TimeFramesMinutes))


def get_config_time_frame(config) -> list:
    """
    Get the time frame config list
    Warning: requires EvaluatorCreator.init_time_frames_from_strategies(self.config) to be called previously
    :param config: the config
    :return: the time frame config list
    """
    return config[constants.CONFIG_TIME_FRAME]


def sort_time_frames(time_frames, reverse=False) -> list:
    """
    Sort a time frame list, shorted to longest
    :param time_frames: the time frames to sort
    :param reverse: if the sort should be reversed
    :return: the time frame list sorted
    """
    return _sort_time_frames(time_frames, reverse)


def sort_config_time_frames(config) -> None:
    """
    Sort the time frame config and save it in config
    :param config: the config
    """
    config[constants.CONFIG_TIME_FRAME] = sort_time_frames(
        config[constants.CONFIG_TIME_FRAME]
    )


def get_display_time_frame(config, default_display_time_frame):
    """
    Get display time frame
    :param config: the config
    :param default_display_time_frame: the default time frame display
    :return: the time frame display
    """
    if default_display_time_frame in get_config_time_frame(config):
        return default_display_time_frame
    # else: return largest time frame
    return config[constants.CONFIG_TIME_FRAME][-1]


def get_previous_time_frame(config_time_frames, time_frame, origin_time_frame):
    """
    Get the previous time frame
    :param config_time_frames: the time frame config
    :param time_frame: the specified time frame
    :param origin_time_frame: the origin time frame list
    :return: the previous time frame of the specified time frame
    """
    current_time_frame_index = TimeFramesRank.index(time_frame)

    if current_time_frame_index > 0:
        previous = TimeFramesRank[current_time_frame_index - 1]
        if previous in config_time_frames:
            return previous
        return get_previous_time_frame(config_time_frames, previous, origin_time_frame)
    if time_frame in config_time_frames:
        return time_frame
    return origin_time_frame


def find_min_time_frame(time_frames, min_time_frame=None):
    """
    Find the minimum time frame
    :param time_frames: the time frame list
    :param min_time_frame: the min time frame
    :return: the minimal time frame
    """
    time_frame_list = time_frames
    if time_frames and isinstance(next(iter(time_frames)), enums.TimeFrames):
        time_frame_list = [t.value for t in time_frames]

    if (
        not time_frame_list
    ):  # if exchange has no time frame list, returns minimal time frame
        return TimeFramesRank[0]

    min_index = 0
    if min_time_frame:
        min_index = TimeFramesRank.index(min_time_frame)
    # TimeFramesRank is the ordered list of timeframes
    for index, time_frame in enumerate(TimeFramesRank):
        tf_val = time_frame.value
        if index >= min_index and tf_val in time_frame_list:
            try:
                return enums.TimeFrames(tf_val)
            except ValueError:
                pass
    return min_time_frame


def parse_time_frames(time_frames_string_list):
    """
    Parse a time frame list as string
    :param time_frames_string_list: the time frame list as string
    :return: the parsed time frame list
    """
    result_list = []
    for time_frame_string in time_frames_string_list:
        try:
            result_list.append(enums.TimeFrames(time_frame_string))
        except ValueError:
            logging_util.get_logger(LOGGER_TAG).error(
                "No time frame available for: '{0}'. Available time "
                "frames are: {1}. '{0}' time frame requirement "
                "ignored.".format(
                    time_frame_string, [t.value for t in enums.TimeFrames]
                )
            )
    return result_list


def is_time_frame(value):
    """
    :return: True if the value represents a TimeFrame
    """
    try:
        enums.TimeFrames(value)
        return True
    except ValueError:
        return False


def get_last_timeframe_time(
    time_frame: enums.TimeFrames, base_timestamp: float
) -> float:
    """
    :return: the exact timestamp of the last give time_frame tick relatively to the given base_timestamp
    """
    tf_seconds = enums.TimeFramesMinutes[time_frame] * constants.MINUTE_TO_SECONDS
    return base_timestamp - (base_timestamp % tf_seconds)
