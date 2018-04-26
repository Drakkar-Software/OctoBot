import time

from config.cst import CONFIG_TIME_FRAME, TimeFrames, CONFIG_REFRESH_RATE
from evaluator.RealTime import RealTimeTAEvaluator


class WhalesOrderBookEvaluator(RealTimeTAEvaluator):
    def __init__(self, exchange_inst, symbol):
        super().__init__(exchange_inst, symbol)

    def _refresh_data(self):
        pass

    def eval_impl(self):
        pass

    def set_default_config(self):
        self.specific_config = {
            CONFIG_REFRESH_RATE: 5,
            CONFIG_TIME_FRAME: TimeFrames.FIVE_MINUTES
        }
