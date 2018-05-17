import logging

import pandas
from ccxt import OrderNotFound, BaseError

from config.cst import *
from trading.exchanges.websockets.abstract_websocket_manager import AbstractWebSocketManager

# https://github.com/ccxt/ccxt/wiki/Manual#api-methods--endpoints
from tools.time_frame_manager import TimeFrameManager


class Exchange:
    def __init__(self, config, exchange_type, connect_to_online_exchange=True):
        self.ready = False
        self.exchange_type = exchange_type
        self.connect_to_online_exchange = connect_to_online_exchange
        self.client = None
        self.websocket_client = None
        self.config = config
        self.info_list = None
        self.free = None
        self.used = None
        self.total = None
        self.time_frames = []
        self.name = self.exchange_type.__name__
        self.traded_pairs = []

        if self.connect_to_online_exchange:
            self.create_client()

            self.client.load_markets()

        self.all_currencies_price_ticker = None

        # prepare
        self._set_config_time_frame()
        self._set_config_traded_pairs()

        self.logger = logging.getLogger(self.name)

        if self.connect_to_online_exchange:
            self.create_websocket_client_if_possible()
            self.init_web_sockets()
            self.websocket_client.start_sockets()

        self.ready = True

    def enabled(self):
        # if we can get candlestick data
        if not self.connect_to_online_exchange \
                or (self.name in self.config[CONFIG_EXCHANGES] and self.client.has['fetchOHLCV']):
            return True
        else:
            self.logger.warning("Exchange {0} is currently disabled".format(self.name))
            return False

    def create_client(self):
        if self.check_config():
            if self.connect_to_online_exchange:
                self.client = self.exchange_type({
                    'apiKey': self.config["exchanges"][self.name]["api-key"],
                    'secret': self.config["exchanges"][self.name]["api-secret"],
                    'verbose': False,
                    'enableRateLimit': True
                })
            else:
                self.client = self.exchange_type({'verbose': False})
        else:
            self.client = self.exchange_type({'verbose': False})
        self.client.logger.setLevel(logging.INFO)

    def create_websocket_client_if_possible(self):
        for socket_manager in AbstractWebSocketManager.__subclasses__():
            if socket_manager.get_name() == self.get_name().lower():
                self.websocket_client = socket_manager.get_websocket_client(self.config)

    def init_web_sockets(self):
        if self.websocket_client:
            self.websocket_client.init_all_currencies_prices_web_socket(self.time_frames, self.traded_pairs)

    def check_config(self):
        if not self.config["exchanges"][self.name]["api-key"] \
                and not self.config["exchanges"][self.name]["api-secret"]:
            return False
        else:
            return True

    def get_name(self):
        return self.name

    # 'free':  {           // money, available for trading, by currency
    #         'BTC': 321.00,   // floats...
    #         'USD': 123.00,
    #         ...
    #     },
    #
    #     'used':  { ... },    // money on hold, locked, frozen, or pending, by currency
    #
    #     'total': { ... },    // total (free + used), by currency
    def get_balance(self):
        balance = self.client.fetchBalance()

        # store portfolio global info
        self.info_list = balance[CONFIG_PORTFOLIO_INFO]
        self.free = balance[CONFIG_PORTFOLIO_FREE]
        self.used = balance[CONFIG_PORTFOLIO_USED]
        self.total = balance[CONFIG_PORTFOLIO_TOTAL]

        # remove not currency specific keys
        balance.pop(CONFIG_PORTFOLIO_INFO, None)
        balance.pop(CONFIG_PORTFOLIO_FREE, None)
        balance.pop(CONFIG_PORTFOLIO_USED, None)
        balance.pop(CONFIG_PORTFOLIO_TOTAL, None)

        return balance

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        if limit:
            candles = self.client.fetch_ohlcv(symbol, time_frame.value, limit=limit)
        else:
            candles = self.client.fetch_ohlcv(symbol, time_frame.value)

        if data_frame:
            return self.candles_array_to_data_frame(candles)
        else:
            return candles

    @staticmethod
    def candles_array_to_data_frame(candles_array):
        prices = {PriceStrings.STR_PRICE_HIGH.value: [],
                  PriceStrings.STR_PRICE_LOW.value: [],
                  PriceStrings.STR_PRICE_OPEN.value: [],
                  PriceStrings.STR_PRICE_CLOSE.value: [],
                  PriceStrings.STR_PRICE_VOL.value: [],
                  PriceStrings.STR_PRICE_TIME.value: []}

        for c in candles_array:
            prices[PriceStrings.STR_PRICE_TIME.value].append(float(c[PriceIndexes.IND_PRICE_TIME.value]))
            prices[PriceStrings.STR_PRICE_OPEN.value].append(float(c[PriceIndexes.IND_PRICE_OPEN.value]))
            prices[PriceStrings.STR_PRICE_HIGH.value].append(float(c[PriceIndexes.IND_PRICE_HIGH.value]))
            prices[PriceStrings.STR_PRICE_LOW.value].append(float(c[PriceIndexes.IND_PRICE_LOW.value]))
            prices[PriceStrings.STR_PRICE_CLOSE.value].append(float(c[PriceIndexes.IND_PRICE_CLOSE.value]))
            prices[PriceStrings.STR_PRICE_VOL.value].append(float(c[PriceIndexes.IND_PRICE_VOL.value]))

        return pandas.DataFrame(data=prices)

    # return up to ten bidasks on each side of the order book stack
    def get_order_book(self, symbol, limit=30):
        return self.client.fetchOrderBook(symbol, limit)

    def get_recent_trades(self, symbol):
        try:
            return self.client.fetch_trades(symbol)
        except BaseError as e:
            self.logger.error("Failed to get recent trade {0}".format(e))
            return None

    def get_market_price(self, symbol):
        order_book = self.get_order_book(symbol)
        bid = order_book['bids'][0][0] if len(order_book['bids']) > 0 else None
        ask = order_book['asks'][0][0] if len(order_book['asks']) > 0 else None
        spread = (ask - bid) if (bid and ask) else None
        return {'bid': bid, 'ask': ask, 'spread': spread}

    # A price ticker contains statistics for a particular market/symbol for the last instant
    def get_last_price_ticker(self, symbol):
        if self.websocket_client and self.websocket_client.last_price_ticker_is_initialized(symbol):
            return self.websocket_client.get_last_price_ticker(symbol)
        else:
            try:
                return self.client.fetch_ticker(symbol)[ExchangeConstantsTickersColumns.LAST.value]
            except BaseError as e:
                self.logger.error("Failed to get_price_ticker {0}".format(e))
                return None

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    def get_price_ticker(self, symbol):
        try:
            return self.client.fetch_ticker(symbol)
        except BaseError as e:
            self.logger.error("Failed to get_price_ticker {0}".format(e))
            return None

    def get_all_currencies_price_ticker(self):
        try:
            self.all_currencies_price_ticker = self.client.fetch_tickers()
            return self.all_currencies_price_ticker
        except BaseError as e:
            self.logger.error("Failed to get_all_currencies_price_ticker {0}".format(e))
            return None

    # ORDERS
    # {
    #     'id':        '12345-67890:09876/54321', // string
    #     'datetime':  '2017-08-17 12:42:48.000', // ISO8601 datetime with milliseconds
    #     'timestamp':  1502962946216, // order placing/opening Unix timestamp in milliseconds
    #     'status':    'open',         // 'open', 'closed', 'canceled'
    #     'symbol':    'ETH/BTC',      // symbol
    #     'type':      'limit',        // 'market', 'limit'
    #     'side':      'buy',          // 'buy', 'sell'
    #     'price':      0.06917684,    // float price in quote currency
    #     'amount':     1.5,           // ordered amount of base currency
    #     'filled':     1.1,           // filled amount of base currency
    #     'remaining':  0.4,           // remaining amount to fill
    #     'cost':       0.076094524,   // 'filled' * 'price'
    #     'trades':   [ ... ],         // a list of order trades/executions
    #     'fee':      {                // fee info, if available
    #         'currency': 'BTC',       // which currency the fee is (usually quote)
    #         'cost': 0.0009,          // the fee amount in that currency
    #         'rate': 0.002,           // the fee rate (if available)
    #     },
    #     'info':     { ... },         // the original unparsed order structure as is
    # }
    def get_order(self, order_id):
        if self.client.has['fetchOrder']:
            return self.client.fetch_order(order_id)
        else:
            raise Exception("This exchange doesn't support fetchOrder")

    def get_all_orders(self, symbol=None, since=None, limit=None):
        if self.client.has['fetchOrders']:
            return self.client.fetchOrders(symbol=symbol, since=since, limit=limit, params={})
        else:
            raise Exception("This exchange doesn't support fetchOrders")

    def get_open_orders(self, symbol=None, since=None, limit=None):
        if self.client.has['fetchOpenOrders']:
            return self.client.fetchOpenOrders(symbol=symbol, since=since, limit=limit, params={})
        else:
            raise Exception("This exchange doesn't support fetchOpenOrders")

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        if self.client.has['fetchClosedOrders']:
            return self.client.fetchClosedOrders(symbol=symbol, since=since, limit=limit, params={})
        else:
            raise Exception("This exchange doesn't support fetchClosedOrders")

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        return self.client.fetchMyTrades(symbol=symbol, since=since, limit=limit, params={})

    def cancel_order(self, order_id, symbol=None):
        try:
            self.client.cancel_order(order_id, symbol=symbol)
            return True
        except OrderNotFound:
            self.logger.error("Order {0} was not found".format(order_id))
            return False

    # todo { 'type': 'trailing-stop' }
    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        try:
            if order_type == TraderOrderType.BUY_MARKET:
                return self.client.create_market_buy_order(symbol, quantity)
            elif order_type == TraderOrderType.BUY_LIMIT:
                return self.client.create_limit_buy_order(symbol, quantity, price)
            elif order_type == TraderOrderType.SELL_MARKET:
                return self.client.create_market_sell_order(symbol, quantity)
            elif order_type == TraderOrderType.SELL_LIMIT:
                return self.client.create_limit_sell_order(symbol, quantity, price)
            elif order_type == TraderOrderType.STOP_LOSS:
                return None
            elif order_type == TraderOrderType.STOP_LOSS_LIMIT:
                return None
            elif order_type == TraderOrderType.TAKE_PROFIT:
                return None
            elif order_type == TraderOrderType.TAKE_PROFIT_LIMIT:
                return None
        except Exception as e:
            self.logger.error("Failed to create order : {0}".format(e))

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

    def _set_config_time_frame(self):
        for time_frame in TimeFrameManager.get_config_time_frame(self.config):
            if self.time_frame_exists(time_frame.value):
                self.time_frames.append(time_frame)

    def get_config_time_frame(self):
        return self.time_frames

    def _set_config_traded_pairs(self):
        for cryptocurrency in self.config[CONFIG_CRYPTO_CURRENCIES]:
            for symbol in self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_PAIRS]:
                if self.symbol_exists(symbol):
                    self.traded_pairs.append(symbol)

    def get_traded_pairs(self):
        return self.traded_pairs

    def get_rate_limit(self):
        return self.exchange_type.rateLimit / 1000
