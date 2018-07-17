import logging

from ccxt import OrderNotFound, BaseError

from config.cst import *
from trading.exchanges.abstract_exchange import AbstractExchange
from config.cst import ExchangeConstantsMarketStatusColumns as Ecmsc


class RESTExchange(AbstractExchange):
    def __init__(self, config, exchange_type, exchange_manager):
        super().__init__(config, exchange_type)
        self.exchange_manager = exchange_manager

        # ccxt client
        self.client = None

        # balance additional info
        self.info_list = None
        self.free = None
        self.used = None
        self.total = None

        # We will need to create the rest client and fetch exchange config
        self.create_client()
        self.client.load_markets()

        self.all_currencies_price_ticker = None

    def get_symbol_data(self, symbol):
        return self.exchange_manager.get_symbol_data(symbol)

    def get_personal_data(self):
        return self.exchange_manager.get_personal_data()

    # ccxt exchange instance creation
    def create_client(self):
        if self.exchange_manager.check_config(self.get_name()):
            self.client = self.exchange_type({
                'apiKey': self.config[CONFIG_EXCHANGES][self.name][CONFIG_EXCHANGE_KEY],
                'secret': self.config[CONFIG_EXCHANGES][self.name][CONFIG_EXCHANGE_SECRET],
                'verbose': False,
                'enableRateLimit': True
            })
        else:
            self.client = self.exchange_type({'verbose': False})
            self.logger.error("configuration issue: missing login information !")
        self.client.logger.setLevel(logging.INFO)

    def get_market_status(self, symbol):
        if symbol in self.client.markets:
            return self.fix_market_status(self.client.markets[symbol])
        else:
            self.logger.error(f"Fail to get market status of {symbol}")
            return {}

    @staticmethod
    def fix_market_status(market_status):
        # check precision
        if Ecmsc.PRECISION.value in market_status:
            market_precision = market_status[Ecmsc.PRECISION.value]
            if Ecmsc.PRECISION_COST.value not in market_precision:
                if Ecmsc.PRECISION_PRICE.value in market_precision:
                    market_precision[Ecmsc.PRECISION_COST.value] = market_precision[Ecmsc.PRECISION_PRICE.value]

        # check limits
        if Ecmsc.LIMITS.value in market_status:
            market_limit = market_status[Ecmsc.LIMITS.value]
            if Ecmsc.LIMITS_COST.value not in market_limit:
                if Ecmsc.LIMITS_PRICE.value in market_limit:
                    market_limit[Ecmsc.LIMITS_COST.value] = market_limit[Ecmsc.LIMITS_PRICE.value]

        return market_status

    def get_client(self):
        return self.client

    # total (free + used), by currency
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

        self.get_personal_data().set_portfolio(balance)

    def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        if limit:
            candles = self.client.fetch_ohlcv(symbol, time_frame.value, limit=limit)
        else:
            candles = self.client.fetch_ohlcv(symbol, time_frame.value)

        self.exchange_manager.uniformize_candles_if_necessary(candles)

        self.get_symbol_data(symbol).update_symbol_candles(time_frame, candles, replace_all=True)

    # return up to ten bidasks on each side of the order book stack
    def get_order_book(self, symbol, limit=30):
        self.get_symbol_data(symbol).update_order_book(self.client.fetchOrderBook(symbol, limit))

    def get_recent_trades(self, symbol, limit=50):
        try:
            self.get_symbol_data(symbol).update_recent_trades(self.client.fetch_trades(symbol, limit=limit))
        except BaseError as e:
            self.logger.error(f"Failed to get recent trade {e}")

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    def get_price_ticker(self, symbol):
        try:
            self.get_symbol_data(symbol).update_symbol_ticker(self.client.fetch_ticker(symbol))
        except BaseError as e:
            self.logger.error(f"Failed to get_price_ticker {e}")

    def get_all_currencies_price_ticker(self):
        try:
            self.all_currencies_price_ticker = self.client.fetch_tickers()
            return self.all_currencies_price_ticker
        except BaseError as e:
            self.logger.error(f"Failed to get_all_currencies_price_ticker {e}")
            return None

    # ORDERS
    def get_order(self, order_id, symbol=None):
        if self.client.has['fetchOrder']:
            self.get_personal_data().upsert_order(order_id, self.client.fetch_order(order_id, symbol))
        else:
            raise Exception("This exchange doesn't support fetchOrder")

    def get_all_orders(self, symbol=None, since=None, limit=None):
        if self.client.has['fetchOrders']:
            self.get_personal_data().upsert_orders(self.client.fetchOrders(symbol=symbol, since=since, limit=limit))
        else:
            raise Exception("This exchange doesn't support fetchOrders")

    def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        if self.client.has['fetchOpenOrders']:
            self.get_personal_data().upsert_orders(self.client.fetchOpenOrders(symbol=symbol, since=since, limit=limit))
        else:
            raise Exception("This exchange doesn't support fetchOpenOrders")

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        if self.client.has['fetchClosedOrders']:
            self.get_personal_data().upsert_orders(self.client.fetchClosedOrders(symbol=symbol, since=since, limit=limit))
        else:
            raise Exception("This exchange doesn't support fetchClosedOrders")

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        return self.client.fetchMyTrades(symbol=symbol, since=since, limit=limit)

    def cancel_order(self, order_id, symbol=None):
        try:
            self.client.cancel_order(order_id, symbol=symbol)
            return True
        except OrderNotFound:
            self.logger.error(f"Order {order_id} was not found")
        except Exception as e:
            self.logger.error(f"Order {order_id} failed to cancel | {e}")
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
            order_desc = f"order_type: {order_type}, symbol: {symbol}, quantity: {quantity}, price: {price}," \
                         f" stop_price: {stop_price}"
            self.logger.error(f"Failed to create order : {e} ({order_desc})")
        return None

    def get_uniform_timestamp(self, timestamp):
        return timestamp / 1000
