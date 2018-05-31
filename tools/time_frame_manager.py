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
