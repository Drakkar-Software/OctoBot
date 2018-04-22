import numpy


class AnalysisUtil:

    @staticmethod
    def normalize_data_frame(data_frame):
        return (data_frame - data_frame.mean()) / (data_frame.max() - data_frame.min())

    @staticmethod
    def get_estimation_of_move_state_relatively_to_previous_moves_length(mean_crossing_indexes, pattern_move_size=1):

        # compute average move size
        time_averages = [(lambda a: mean_crossing_indexes[a+1]-mean_crossing_indexes[a])(a)
                         for a in range(len(mean_crossing_indexes)-1)]
        time_average = numpy.mean(time_averages)*pattern_move_size

        # higher than time_average => high chances to be at half of the move already
        if time_averages[-1] > time_average/2:
            return 1
        else:
            return time_averages[-1] / (time_average/2)

    @staticmethod
    def get_threshold_change_indexes(data_frame, threshold):

        # sub threshold values
        sub_threshold_indexes = data_frame.index[data_frame <= threshold]

        # remove consecutive sub-threshold values because they are not crosses
        threshold_crossing_indexes = []
        current_move_size = 1
        for i in range(len(sub_threshold_indexes)):
            index = sub_threshold_indexes[i]
            if not len(threshold_crossing_indexes):
                threshold_crossing_indexes.append(index)
            else:
                if threshold_crossing_indexes[-1] == index - current_move_size:
                    current_move_size += 1
                else:
                    threshold_crossing_indexes.append(sub_threshold_indexes[i-1])
                    threshold_crossing_indexes.append(index)
                    current_move_size = 1
        # add last index if data_frame ends above threshold and last threshold_crossing_indexes inferior
        # to data_frame size
        if sub_threshold_indexes[-1] < len(data_frame.index) and data_frame.iloc[-1] > threshold:
            threshold_crossing_indexes.append(sub_threshold_indexes[-1]+1)

        return threshold_crossing_indexes
