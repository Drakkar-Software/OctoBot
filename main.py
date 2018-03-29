from threading import Thread
from time import sleep

from botcore.config.config import load_config

from exchanges.binance import *
from lib.indicator import *


def main():
    config = load_config()
    binance_exchange = BinanceExchange(config)
    time_frame = TimeFrames.ONE_MINUTE
    thread = Thread(target=binance_williams_r, args=(binance_exchange, time_frame))
    thread.start()
    thread.join()


def binance_williams_r(binance_exchange, time_frame):
    while(True):
        binance_enum_time_frame = binance_exchange.get_time_frame_enum()
        data = binance_exchange.get_symbol_prices("BTCUSDT", binance_enum_time_frame(time_frame))
        print(williams_r(data))
        sleep(time_frame.value * 1000)


if __name__ == '__main__':
    main()
