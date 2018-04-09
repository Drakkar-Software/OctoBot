import ccxt
import pandas

from config.cst import PriceStrings, MARKET_SEPARATOR


class Exchange:
    def __init__(self, config, exchange_type):
        self.exchange_type = exchange_type
        self.client = None
        self.config = config
        self.name = self.exchange_type.__name__
        self.create_client()
        self.client.load_markets()

        # time.sleep (exchange.rateLimit / 1000) # time.sleep wants seconds

    def enabled(self):
        # if we can get candlestick data
        if self.name in self.config["exchanges"] and self.client.has['fetchOHLCV']:
            return True
        else:
            return False

    def create_client(self):
        if self.check_config():
            self.client = self.exchange_type({
                'apiKey': self.config["exchanges"][self.name]["api-key"],
                'secret': self.config["exchanges"][self.name]["api-secret"],
            })
        else:
            self.client = self.exchange_type()

    def check_config(self):
        if not self.config["exchanges"][self.name]["api-key"] \
                and not self.config["exchanges"][self.name]["api-secret"]:
            return False
        else:
            return True

    def get_symbol_prices(self, symbol, time_frame):
        candles = self.client.fetch_ohlcv(symbol, time_frame.value)

        prices = {PriceStrings.STR_PRICE_HIGH.value: [],
                  PriceStrings.STR_PRICE_LOW.value: [],
                  PriceStrings.STR_PRICE_OPEN.value: [],
                  PriceStrings.STR_PRICE_CLOSE.value: [],
                  PriceStrings.STR_PRICE_VOL.value: [],
                  PriceStrings.STR_PRICE_TIME.value: []}

        for c in candles:
            prices[PriceStrings.STR_PRICE_TIME.value].append(float(c[0]))
            prices[PriceStrings.STR_PRICE_OPEN.value].append(float(c[1]))
            prices[PriceStrings.STR_PRICE_HIGH.value].append(float(c[2]))
            prices[PriceStrings.STR_PRICE_LOW.value].append(float(c[3]))
            prices[PriceStrings.STR_PRICE_CLOSE.value].append(float(c[4]))
            prices[PriceStrings.STR_PRICE_VOL.value].append(float(c[5]))

        return pandas.DataFrame(data=prices)

    def update_balance(self, symbol):
        raise NotImplementedError("Update_balance not implemented")

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        raise NotImplementedError("Update_balance not implemented")

    def get_all_orders(self):
        raise NotImplementedError("Get_all_orders not implemented")

    def get_order(self, order_id):
        raise NotImplementedError("Get_order not implemented")

    def get_open_orders(self):
        raise NotImplementedError("Get_open_orders not implemented")

    def cancel_order(self, order_id):
        raise NotImplementedError("Cancel_order not implemented")

    def get_trade_history(self):
        raise NotImplementedError("Get_trade_history not implemented")

    def get_recent_trades(self, symbol):
        return self.client.fetch_trades(symbol)

    def get_name(self):
        return self.name

    def symbol_exists(self, symbol):
        if symbol in self.client.symbols:
            return True
        else:
            return False

    def time_frame_exists(self, time_frame):
        if time_frame in self.client.timeframes:
            return True
        else:
            return False

    # Return currency, market
    @staticmethod
    def split_symbol(symbol):
        splitted = symbol.split(MARKET_SEPARATOR)
        return splitted[0], splitted[1]