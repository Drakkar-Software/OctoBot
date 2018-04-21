import numpy


class AnalysisUtil:

    @staticmethod
    def normalize_data_frame(data_frame):
        return (data_frame - data_frame.mean()) / (data_frame.max() - data_frame.min())

    @staticmethod
    def get_estimation_of_move_state_relatively_to_previous_moves_length(mean_crossing_indexes):

        # compute average move size
        time_averages = [(lambda a: mean_crossing_indexes[a+1]-mean_crossing_indexes[a])(a)
                         for a in range(len(mean_crossing_indexes)-1)]
        time_average = numpy.mean(time_averages)

        # higher than time_average => high chances to be at half of the move already
        if time_averages[-1] > time_average/2:
            return 1
        else:
            return time_averages[-1] / (time_average/2)

    @staticmethod
    def get_sign_change_indexes(data_frame):

        # get zero and negative values
        sub_zero_indexes = data_frame.index[data_frame <= 0]

        # remove consecutive sub-zero values because they are not crosses
        zero_crossing_indexes = []
        current_move_size = 1
        for index in sub_zero_indexes:
            if not len(zero_crossing_indexes):
                zero_crossing_indexes.append(index)
            else:
                if zero_crossing_indexes[-1] == index - current_move_size:
                    current_move_size += 1
                else:
                    zero_crossing_indexes.append(index)
                    current_move_size = 1
        return zero_crossing_indexes
