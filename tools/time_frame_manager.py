import logging

from config.cst import TimeFramesMinutes, TimeFrames, CONFIG_TIME_FRAME


class TimeFrameManager:
    TimeFramesRank = sorted(TimeFramesMinutes, key=TimeFramesMinutes.__getitem__)

    @staticmethod
    def get_config_time_frame(config):
        if CONFIG_TIME_FRAME in config:
            result = []
            for time_frame in config[CONFIG_TIME_FRAME]:
                try:
                    result.append(TimeFrames(time_frame))
                except ValueError:
                    logging.warning("Time frame not found : {0}".format(time_frame))
            return result
        else:
            return TimeFrames

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
    def find_config_min_time_frame(config_time_frames):
        # TimeFramesRank is the ordered list of timeframes
        for tf in TimeFrameManager.TimeFramesRank:
            if tf in config_time_frames:
                try:
                    return TimeFrames(tf)
                except ValueError:
                    pass
        return TimeFrames.ONE_MINUTE
