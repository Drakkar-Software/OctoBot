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

        self.symbols_social_threads = []
        self.symbols_TA_threads = []

    def create_evaluation_threads(self):
        self.logger.info("Evaluation threads creation...")

        for symbol in self.symbols:

            #1 TA
            current_symbols_threads = []
            at_least_one_TA=False
            for exchange_type in self.exchanges:
                exchange_inst = exchange_type(self.config)

                if exchange_inst.enabled():
                    exchange_inst.get_symbol_list()
                    # Verify that symbol exists on this exchange
                    if exchange_inst.symbol_exists(symbol):

                        # create trader instance for this exchange
                        exchange_trader = Trader(self.config, exchange_inst)

                        for time_frame in self.time_frames:
                            at_least_one_TA=True
                            current_symbols_threads.append(TAEvaluatorThread(self.config,
                                                                        symbol,
                                                                        time_frame,
                                                                        exchange_inst,
                                                                        self.notifier,
                                                                        exchange_trader))

                    # notify that exchanges doesn't support this symbol
                    else:
                        self.logger.warning(exchange_type.__name__ + " doesn't support " + symbol)
            #2 Social
            if at_least_one_TA:
                self.symbols_TA_threads.extend(current_symbols_threads)
                self.symbols_social_threads.append(SocialEvaluatorThread(self.config,
                                                               symbol,
                                                               TimeFrames.ONE_HOUR,
                                                               self.notifier,
                                                               current_symbols_threads))


    def start_threads(self):
        for thread in self.symbols_TA_threads:
            thread.start()
        for thread in self.symbols_social_threads:
            thread.start()
        self.logger.info("Evaluation threads started...")

    def join_threads(self):
        for thread in self.symbols_TA_threads:
            thread.join()
