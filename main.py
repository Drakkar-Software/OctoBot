from binance.client import Client
from botcore.config.config import load_config


def main():
    config = load_config("config.json")
    client = Client(config["exchanges"]["binance"]["api-key"],
                    config["exchanges"]["binance"]["api-secret"],
                    {"verify": True, "timeout": 20})
    print(client.get_historical_trades(symbol='BTCUSDT'))


if __name__ == '__main__':
    main()
