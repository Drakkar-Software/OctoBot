from config.cst import *


class ExchangeData:
    ORDERS_KEY = "orders"

    TIME_FRAME_CANDLE_TIME = "candle_time"
    TIME_FRAME_DATA = "data"

    # note: symbol keys are without /
    def __init__(self):
        self.symbol_prices = {}
        self.symbol_tickers = {}
        self.portfolio = {}
        self.orders = {}
        self.is_initialized = {
            self.ORDERS_KEY: False
        }

    def add_price(self, symbol, time_frame, start_candle_time, price_data):
        if symbol not in self.symbol_prices:
            self.symbol_prices[symbol] = {}
        prices_per_time_frames = self.symbol_prices[symbol]
        if time_frame not in prices_per_time_frames:
            prices_per_time_frames[time_frame] = [{self.TIME_FRAME_CANDLE_TIME: start_candle_time,
                                                   self.TIME_FRAME_DATA: price_data}]
        else:
            time_frame_data = prices_per_time_frames[time_frame]
            # add new candle if previous candle is done
            if time_frame_data[-1][self.TIME_FRAME_CANDLE_TIME] < start_candle_time:
                time_frame_data.append({self.TIME_FRAME_CANDLE_TIME: start_candle_time,
                                        self.TIME_FRAME_DATA: price_data})
            # else update current candle
            else:
                time_frame_data[-1][self.TIME_FRAME_DATA] = price_data

    def update_portfolio(self, currency, total, available, in_order):
        self.portfolio[currency] = {
            CONFIG_PORTFOLIO_TOTAL: total,
            CONFIG_PORTFOLIO_FREE: available,
            CONFIG_PORTFOLIO_USED: in_order
        }

    def set_ticker(self, symbol, ticker_data):
        self.symbol_tickers[symbol] = ticker_data

    # maybe later add an order remover to free up memory ?
    def upsert_order(self, order_id, ccxt_order):
        self.orders[order_id] = ccxt_order

    def get_all_orders(self, symbol, since, limit):
        return self._select_orders(None, symbol, since, limit)

    def get_open_orders(self, symbol, since, limit):
        return self._select_orders("open", symbol, since, limit)

    def get_closed_orders(self, symbol, since, limit):
        return self._select_orders("closed", symbol, since, limit)

    def initialize(self, symbol, symbol_data, time_frame):
        pass

    def is_initialized(self, symbol):
        return self.is_initialized[symbol]

    # temporary method awaiting for symbol "/" reconstruction in ws
    @staticmethod
    def _adapt_symbol(symbol):
        return symbol.replace("/", "")

    def _select_orders(self, state, symbol, since, limit):
        orders = [
            order
            for order in self.orders.values()
            if (
                    (state is None or order["status"] == state) and
                    (symbol is None or (symbol and order["symbol"] == symbol)) and
                    (since is None or (since and order['timestamp'] < since))
            )
        ]
        if limit is not None:
            return orders[0:limit]
        else:
            return orders
