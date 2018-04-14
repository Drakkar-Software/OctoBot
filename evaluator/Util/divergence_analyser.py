class DivergenceAnalyser:

    @staticmethod
    # TODO
    def detect(data_frame, indicator_data_frame, candle_num):
        candle_data = data_frame.tail(candle_num)
        indicator_data = indicator_data_frame.tail(candle_num)

        total_delta = []

        for i in range(0, candle_num - 1):
            candle_delta = candle_data.values[i] - candle_data.values[i+1]
            indicator_delta = indicator_data.values[i] - indicator_data.values[i+1]
            total_delta.append(candle_delta - indicator_delta)
