import logging
import threading
import time

from evaluator import *


class EvaluatorThread(threading.Thread):
    def __init__(self, config, symbol, time_frame, exchange):
        threading.Thread.__init__(self)
        self.config = config
        self.exchange = exchange
        self.exchange_time_frame = self.exchange.get_time_frame_enum()
        self.symbol = symbol
        self.time_frame = time_frame

        self.thread_name = "THREAD - " + self.symbol \
                           + " - " + self.exchange.__class__.__name__ \
                           + " - " + str(self.time_frame)
        self.logger = logging.getLogger(self.thread_name)

        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_history_time(self.time_frame.value)

    def run(self):
        while True:
            self.evaluator.set_data(self.exchange.get_symbol_prices(self.symbol,
                                                                    self.exchange_time_frame(self.time_frame)))
            self.logger.debug("Social Eval : " + str(self.evaluator.social_eval()))
            self.logger.debug("TA Eval : " + str(self.evaluator.ta_eval()))

            self.evaluator.finalize()
            self.logger.debug("DECISION : " + str(self.evaluator.decide()))

            time.sleep(self.time_frame.value * MINUTE_TO_SECONDS)
