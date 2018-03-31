from botcore.config.config import load_config

from evaluator import *
from exchanges import *


# Eval > 0.5 --> go short
# Eval < 0.5 --> go long
def main():
    # TODO : TEMP LOCATION / Config
    config = load_config()
    time_frame = TimeFrames.ONE_MINUTE
    symbols = ["BTCUSDT", "ETHUSDT"]

    # TODO : TEMP LOCATION / Exchange get data --> binance
    binance_exchange = BinanceExchange(config)
    binance_enum_time_frame = binance_exchange.get_time_frame_enum()

    # THREADS
    symbol_threads = []

    # TODO for each time frame

    # create symbol threads
    for symbol in symbols:
        symbol_threads.append(EvaluatorThread(config, symbol, time_frame, binance_exchange, binance_enum_time_frame))

    # start threads
    for thread in symbol_threads:
        thread.start()

    # join threads
    for thread in symbol_threads:
        thread.join()


if __name__ == '__main__':
    main()
