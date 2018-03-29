from botcore.config.config import load_config

from exchanges.binance import BinanceExchange


def main():
    config = load_config("config.json")
    binance_exchange = BinanceExchange(config)


if __name__ == '__main__':
    main()
