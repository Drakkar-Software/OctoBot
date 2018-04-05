import time

from evaluator.RealTime.realtime_evaluator import RealTimeTAEvaluator

from config.cst import *


class InstantFluctuationsEvaluator(RealTimeTAEvaluator):
    def __init__(self, exchange_inst, symbol):
        super().__init__(exchange_inst, symbol)
        self.enabled = True

    def refresh_data(self):
        self.exchange.get_symbol_prices(
            self.symbol,
            self.exchange_time_frame(self.specific_config[CONFIG_TIME_FRAME]))

    def eval(self):
        self.is_updating = True
        # example !
        # check last candle
        self.eval_note = 0.42
        something_is_happening = False
        if something_is_happening:
            self.notify_evaluator_threads(self.__class__.__name__)
        self.is_updating = False

    def set_default_config(self):
        self.specific_config = {
            CONFIG_REFRESH_RATE: 5,
            CONFIG_TIME_FRAME: TimeFrames.FIVE_MINUTES
        }

    def run(self):
        while True:
            self.refresh_data()
            self.eval()
            time.sleep(self.specific_config[CONFIG_REFRESH_RATE])
