import time

from config.cst import CONFIG_TIME_FRAME, TimeFrames, CONFIG_REFRESH_RATE
from evaluator.RealTime import RealTimeTAEvaluator


class WhalesOrderBookEvaluator(RealTimeTAEvaluator):
    def __init__(self, exchange_inst, symbol):
        super().__init__(exchange_inst, symbol)

    def refresh_data(self):
        self.exchange.get_symbol_prices(
            self.symbol,
            self.specific_config[CONFIG_TIME_FRAME])

    def eval_impl(self):
        # example !
        # check orderbook whales
        self.eval_note = 0.42
        something_is_happening = True
        if something_is_happening:
            self.notify_evaluator_threads(self.__class__.__name__)

    def set_default_config(self):
        self.specific_config = {
            CONFIG_REFRESH_RATE: 5,
            CONFIG_TIME_FRAME: TimeFrames.FIVE_MINUTES
        }

    def run(self):
        while self.keep_running:
            self.refresh_data()
            self.eval()
            time.sleep(self.specific_config[CONFIG_REFRESH_RATE])
