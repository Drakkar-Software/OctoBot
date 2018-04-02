from logging.config import fileConfig

from botcore.config.config import load_config

from evaluator import *
from exchanges import *

# Eval > 0.5 --> go short
# Eval < 0.5 --> go long
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
        self.time_frames = [TimeFrames.ONE_HOUR, TimeFrames.FOUR_HOURS, TimeFrames.ONE_DAY]
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        self.exchanges = [BinanceExchange]

        # Notifier
        self.notifier = Notification(self.config)

        self.symbols_threads = []

    def create_evaluation_threads(self):
        self.logger.info("Evaluation threads creation...")

        for exchange_type in self.exchanges:
            exchange_inst = exchange_type(self.config)

            if exchange_inst.enabled():
                exchange_inst.get_symbol_list()

                # create trader instance for this exchange
                exchange_trader = Trader(self.config, exchange_inst)

                for symbol in self.symbols:
                    # Verify that symbol exists on this exchange
                    if exchange_inst.symbol_exists(symbol):

                        for time_frame in self.time_frames:
                            self.symbols_threads.append(EvaluatorThread(self.config,
                                                                        symbol,
                                                                        time_frame,
                                                                        exchange_inst,
                                                                        self.notifier,
                                                                        exchange_trader))

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
