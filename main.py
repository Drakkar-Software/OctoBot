from logging.config import fileConfig

from botcore.config.config import load_config

from evaluator import *
from exchanges import *


# Eval > 0.5 --> go short
# Eval < 0.5 --> go long
def main():
    # Logger
    fileConfig('config/logging_config.ini')
    logger = logging.getLogger()

    # Config
    logger.info("Load config file...")
    config = load_config()

    # TODO : CONFIG TEMP LOCATION
    time_frames = [TimeFrames.ONE_MINUTE]
    symbols = ["BTCUSDT", "ETHUSDT"]
    exchanges = [BinanceExchange]

    # THREADS
    logger.info("Evaluation threads creation...")
    symbols_threads = []

    # create symbol threads
    for symbol in symbols:

        for exchange_type in exchanges:
            exchange_inst = exchange_type(config)
            exchange_inst.get_symbol_list()

            # Verify that symbol exists on this exchange
            if exchange_inst.symbol_exists(symbol):

                for time_frame in time_frames:
                    symbols_threads.append(EvaluatorThread(config, symbol, time_frame, exchange_inst))

    # start threads
    for thread in symbols_threads:
        thread.start()
    logger.info("Evaluation threads started...")

    # join threads
    for thread in symbols_threads:
        thread.join()


if __name__ == '__main__':
    main()
