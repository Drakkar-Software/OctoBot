from binance.client import Client
from botcore.config.config import load_config

from indicator import *

STR_PRICE_CLOSE = "<CLOSE>"
STR_PRICE_OPEN = "<OPEN>"
STR_PRICE_HIGH = "<HIGH>"
STR_PRICE_LOW = "<LOW>"
STR_PRICE_VOL = "<VOL>"


def main():
    config = load_config("config.json")
    client = Client(config["exchanges"]["binance"]["api-key"],
                    config["exchanges"]["binance"]["api-secret"],
                    {"verify": True, "timeout": 20})

    candles = client.get_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_1DAY)
    prices = {STR_PRICE_HIGH: [], STR_PRICE_LOW: [], STR_PRICE_OPEN: [], STR_PRICE_CLOSE: [], STR_PRICE_VOL: []}

    for c in candles:
        prices[STR_PRICE_OPEN].append(float(c[1]))
        prices[STR_PRICE_HIGH].append(float(c[2]))
        prices[STR_PRICE_LOW].append(float(c[3]))
        prices[STR_PRICE_CLOSE].append(float(c[4]))
        prices[STR_PRICE_VOL].append(float(c[5]))

    df = pd.DataFrame(data=prices)
    print(williams_r(df))



if __name__ == '__main__':
    main()
