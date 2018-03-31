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

    # TODO : TEMP LOCATION
    logger.info("Load config file...")
    config = load_config()
    time_frames = [TimeFrames.ONE_MINUTE]
    symbols = ["BTCUSDT", "ETHUSDT"]
    exchanges = [BinanceExchange]

    # THREADS
    logger.info("Evaluation thread creation...")
    symbols_threads = []

    # create symbol threads
    for symbol in symbols:
        for exchange_type in exchanges:
            exchange_inst = exchange_type(config)
            for time_frame in time_frames:
                symbols_threads.append(EvaluatorThread(config, symbol, time_frame, exchange_inst))

    # start threads
    logger.info("Evaluation thread started...")
    for thread in symbols_threads:
        thread.start()

    # join threads
    for thread in symbols_threads:
        thread.join()


if __name__ == '__main__':
    main()
