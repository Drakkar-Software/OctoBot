from binance.client import Client
from botcore.config.config import load_config

from indicator import *


# https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md

def main():
    config = load_config("config.json")
    client = Client(config["exchanges"]["binance"]["api-key"],
                    config["exchanges"]["binance"]["api-secret"],
                    {"verify": True, "timeout": 20})

    candles = client.get_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_1HOUR)
    prices = {"<CLOSE>": [], "<VOL>": []}

    for c in candles:
        prices["<CLOSE>"].append(float(c[4]))
        prices["<VOL>"].append(float(c[5]))

    df = pd.DataFrame(data=prices)
    print(on_balance_volume(df))


if __name__ == '__main__':
    main()
