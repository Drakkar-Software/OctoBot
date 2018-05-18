from abc import *

from tools.symbol_util import merge_symbol
from config.cst import CONFIG_PORTFOLIO_TOTAL, CONFIG_PORTFOLIO_USED, CONFIG_PORTFOLIO_FREE
from ccxt.base.exchange import Exchange as ccxtExchange


class AbstractWebSocketManager:

    def __init__(self, config):
        self.config = config
        self.client = None
        self.exchange_data = ExchangeData()

    @classmethod
    @abstractmethod
    def get_name(cls):
        raise NotImplementedError("get_name not implemented")

    @staticmethod
    @abstractmethod
    def convert_into_ccxt_order(msg):
        raise NotImplementedError("convert_into_ccxt_order not implemented")

    @staticmethod
    @abstractmethod
    def format_price_ticker(price_ticker):
        raise NotImplementedError("format_price_ticker not implemented")

    @abstractmethod
    def get_last_price_ticker(self, symbol):
        raise NotImplementedError("get_last_price_ticker not implemented")

    @abstractmethod
    def start_sockets(self):
        raise NotImplementedError("start_sockets not implemented")

    @abstractmethod
    def stop_sockets(self):
        raise NotImplementedError("stop_sockets not implemented")

    @abstractmethod
    def get_websocket_client(config):
        raise NotImplementedError("get_websocket_client not implemented")

    @abstractmethod
    def init_all_currencies_prices_web_socket(self, time_frames, trader_pairs):
        raise NotImplementedError("init_all_currencies_klines_web_socket not implemented")

    @abstractmethod
    def init_web_sockets(self, time_frames, trader_pairs):
        raise NotImplementedError("init_web_sockets not implemented")

    def last_price_ticker_is_initialized(self, symbol):
        return merge_symbol(symbol) in self.exchange_data.symbol_tickers

    def currency_database_is_initialized(self, symbol):
        return self.exchange_data.is_initialized(symbol)

    def portfolio_is_initialized(self):
        return self.exchange_data.portfolio

    def orders_are_initialized(self):
        return self.exchange_data.is_initialized[ExchangeData.ORDERS_KEY]

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        pass

    def get_portfolio(self):
        return self.exchange_data.portfolio

    def has_order(self, order_id):
        return order_id in self.exchange_data.orders

    def get_order(self, order_id):
        return self.exchange_data.orders[order_id]

    def get_all_orders(self, symbol, since, limit):
        return self.exchange_data.get_all_orders(symbol, since, limit)

    def get_open_orders(self, symbol, since, limit):
        return self.exchange_data.get_open_orders(symbol, since, limit)

    def get_closed_orders(self, symbol, since, limit):
        return self.exchange_data.get_closed_orders(symbol, since, limit)

    def set_orders_are_initialized(self, value):
        self.exchange_data.is_initialized[ExchangeData.ORDERS_KEY] = value

    def init_ccxt_order_from_other_source(self, ccxt_order):
        self.exchange_data.upsert_order(ccxt_order["id"], ccxt_order)

    def _update_order(self, msg):
        ccxt_order = self.convert_into_ccxt_order(msg)
        self.exchange_data.upsert_order(ccxt_order["id"], ccxt_order)

    # ============== ccxt adaptation methods ==============
    @staticmethod
    @abstractmethod
    def parse_order_status(status):
        raise NotImplementedError("parse_order_status not implemented")

    @staticmethod
    def safe_lower_string(dictionary, key, default_value=None):
        value = AbstractWebSocketManager.safe_string(dictionary, key, default_value)
        if value is not None:
            value = value.lower()
        return value

    @staticmethod
    def safe_string(dictionary, key, default_value=None):
        return ccxtExchange.safe_string(dictionary, key, default_value)

    @staticmethod
    def safe_float(dictionary, key, default_value=None):
        return ccxtExchange.safe_float(dictionary, key, default_value)

    @staticmethod
    def safe_value(dictionary, key, default_value=None):
        return ccxtExchange.safe_value(dictionary, key, default_value)

    @staticmethod
    def iso8601(value):
        return ccxtExchange.iso8601(value)

    # ==============      -------------      ==============


class ExchangeData:

    ORDERS_KEY = "orders"

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
            prices_per_time_frames[time_frame] = [TimeFrameManager(start_candle_time, price_data)]
        else:
            time_frame_data = prices_per_time_frames[time_frame]
            # add new candle if previous candle is done
            if time_frame_data[-1].start_candle_time < start_candle_time:
                time_frame_data.append(TimeFrameManager(start_candle_time, price_data))
            # else update current candle
            else:
                time_frame_data[-1].data = price_data

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


class TimeFrameManager:

    def __init__(self, start_candle_time, data):
        self.start_candle_time = start_candle_time
        self.data = data

