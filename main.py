from botcore.config.config import load_config

from evaluator.evaluator import Evaluator
from exchanges.binance import *


def main():
    # TEMP : Config
    config = load_config()
    time_frame = TimeFrames.ONE_MINUTE
    symbol = "BTCUSDT"

    # TEMP : Exchange get data --> binance
    binance_exchange = BinanceExchange(config)
    binance_enum_time_frame = binance_exchange.get_time_frame_enum()
    data = binance_exchange.get_symbol_prices("BTCUSDT", binance_enum_time_frame(time_frame))

    evaluator = Evaluator()
    evaluator.set_config(config)
    evaluator.set_data(data)
    evaluator.set_symbol(symbol)
    evaluator.set_history_time(time_frame.value)
    evaluator.social_eval()

    # thread = Thread(target=binance_williams_r, args=(binance_exchange, time_frame))
    # thread.start()
    # thread.join()


# def binance_williams_r(binance_exchange, time_frame):
#     while(True):
#         binance_enum_time_frame = binance_exchange.get_time_frame_enum()
#         data = binance_exchange.get_symbol_prices("BTCUSDT", binance_enum_time_frame(time_frame))
#         print(williams_r(data))
#         sleep(time_frame.value * 1000)


if __name__ == '__main__':
    main()
