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

from tools.logging.logging_util import get_logger

from config import TimeFramesMinutes, TimeFrames, CONFIG_TIME_FRAME, DEFAULT_DISPLAY_TIME_FRAME


def _sort_time_frames(time_frames, reverse=False):
    return sorted(time_frames, key=TimeFramesMinutes.__getitem__, reverse=reverse)


class TimeFrameManager:
    TimeFramesRank = _sort_time_frames(TimeFramesMinutes)

    # requires EvaluatorCreator.init_time_frames_from_strategies(self.config) to be called previously
    @staticmethod
    def get_config_time_frame(config):
        return config[CONFIG_TIME_FRAME]

    @staticmethod
    def sort_time_frames(time_frames, reverse=False):
        return _sort_time_frames(time_frames, reverse)

    @staticmethod
    def sort_config_time_frames(config):
        config[CONFIG_TIME_FRAME] = TimeFrameManager.sort_time_frames(config[CONFIG_TIME_FRAME])

    @staticmethod
    def get_display_time_frame(config):
        if DEFAULT_DISPLAY_TIME_FRAME in TimeFrameManager.get_config_time_frame(config):
            return DEFAULT_DISPLAY_TIME_FRAME
        else:
            # else: return largest time frame
            return config[CONFIG_TIME_FRAME][-1]

    @staticmethod
    def get_previous_time_frame(config_time_frames, time_frame, origin_time_frame):
        current_time_frame_index = TimeFrameManager.TimeFramesRank.index(time_frame)

        if current_time_frame_index > 0:
            previous = TimeFrameManager.TimeFramesRank[current_time_frame_index - 1]
            if previous in config_time_frames:
                return previous
            else:
                return TimeFrameManager.get_previous_time_frame(config_time_frames, previous, origin_time_frame)
        else:
            if time_frame in config_time_frames:
                return time_frame
            else:
                return origin_time_frame

    @staticmethod
    def find_min_time_frame(time_frames, min_time_frame=None):
        tf_list = time_frames
        if time_frames and isinstance(next(iter(time_frames)), TimeFrames):
            tf_list = [t.value for t in time_frames]
        min_index = 0
        if min_time_frame:
            min_index = TimeFrameManager.TimeFramesRank.index(min_time_frame)
        # TimeFramesRank is the ordered list of timeframes
        for index, tf in enumerate(TimeFrameManager.TimeFramesRank):
            tf_val = tf.value
            if index >= min_index and tf_val in tf_list:
                try:
                    return TimeFrames(tf_val)
                except ValueError:
                    pass
        return min_time_frame

    @staticmethod
    def parse_time_frames(time_frames_string_list):
        result_list = []
        for time_frame_string in time_frames_string_list:
            try:
                result_list.append(TimeFrames(time_frame_string))
            except ValueError:
                get_logger(TimeFrameManager.__name__).error("No time frame available for: '{0}'. Available time "
                                                            "frames are: {1}. '{0}' time frame requirement "
                                                            "ignored.".
                                                            format(time_frame_string,
                                                                   [t.value for t in TimeFrames]))
        return result_list
