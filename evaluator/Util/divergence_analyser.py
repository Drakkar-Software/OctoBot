from config.cst import DIVERGENCE_USED_VALUE
from evaluator.Util.abstract_util import AbstractUtil


class DivergenceAnalyser(AbstractUtil):

    @staticmethod
    # TODO
    def detect(data_frame, indicator_data_frame):
        candle_data = data_frame.tail(DIVERGENCE_USED_VALUE)
        indicator_data = indicator_data_frame.tail(DIVERGENCE_USED_VALUE)

        total_delta = []

        for i in range(0, DIVERGENCE_USED_VALUE - 1):
            candle_delta = candle_data.values[i] - candle_data.values[i+1]
            indicator_delta = indicator_data.values[i] - indicator_data.values[i+1]
            total_delta.append(candle_delta - indicator_delta)
