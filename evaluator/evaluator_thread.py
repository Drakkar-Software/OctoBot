import threading
import time

from evaluator.evaluator import Evaluator


class EvaluatorThread(threading.Thread):
    def __init__(self, config, symbol, time_frame, exchange, exchange_time_frame):
        threading.Thread.__init__(self)
        self.config = config
        self.exchange = exchange
        self.exchange_time_frame = exchange_time_frame
        self.symbol = symbol
        self.time_frame = time_frame

        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_history_time(self.time_frame.value)

    def run(self):
        self.evaluator.set_data(self.exchange.get_symbol_prices(self.symbol, self.exchange_time_frame(self.time_frame)))
        self.evaluator.social_eval()
        self.evaluator.ta_eval()

        time.sleep(self.time_frame.value * 1000)