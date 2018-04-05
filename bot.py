import logging
from logging.config import fileConfig
from botcore.config.config import load_config
from config.cst import *
from evaluator.evaluator import Evaluator
from evaluator.evaluator_thread import EvaluatorThread
from exchanges import BinanceExchange
from exchanges.trader import Trader
from tools import Notification


class Crypto_Bot:
    def __init__(self):
        # Logger
        fileConfig('config/logging_config.ini')
        self.logger = logging.getLogger()

        # Config
        self.logger.info("Load config file...")
        self.config = load_config()

        # TODO : CONFIG TEMP LOCATION
        self.time_frames = [TimeFrames.ONE_HOUR]
        self.symbols = ["BTCUSDT"]
        self.exchanges = [BinanceExchange]

        # Notifier
        self.notifier = Notification(self.config)

        self.symbols_threads = []
        self.exchange_traders = {}
        self.exchanges_list = {}

    def create_exchange_traders(self):
        for exchange_type in self.exchanges:
            exchange_inst = exchange_type(self.config)

            # create trader instance for this exchange
            exchange_trader = Trader(self.config, exchange_inst)

            self.exchanges_list[exchange_type.__name__] = exchange_inst
            self.exchange_traders[exchange_type.__name__] = exchange_trader

    def create_evaluation_threads(self):
        self.logger.info("Evaluation threads creation...")

        # create Socials and TA evaluators
        for symbol in self.symbols:

            # create Socials Evaluators
            social_eval_list = Evaluator.create_social_eval(self.config, symbol)

            # create TA evaluators
            for exchange_type in self.exchanges:
                exchange_inst = self.exchanges_list[exchange_type.__name__]

                if exchange_inst.enabled():
                    exchange_inst.get_symbol_list()

                    # Verify that symbol exists on this exchange
                    if exchange_inst.symbol_exists(symbol):

                        for time_frame in self.time_frames:
                            self.symbols_threads.append(EvaluatorThread(self.config,
                                                                        symbol,
                                                                        time_frame,
                                                                        exchange_inst,
                                                                        self.notifier,
                                                                        self.exchange_traders[exchange_type.__name__],
                                                                        social_eval_list))

                    # notify that exchanges doesn't support this symbol
                    else:
                        self.logger.warning(exchange_type.__name__ + " doesn't support " + symbol)

    def start_threads(self):
        for thread in self.symbols_threads:
            thread.start()
        self.logger.info("Evaluation threads started...")

    def join_threads(self):
        for thread in self.symbols_threads:
            thread.join()
