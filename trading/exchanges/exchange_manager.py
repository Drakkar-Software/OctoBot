import logging

from config.cst import *
from tools.time_frame_manager import TimeFrameManager
from trading.exchanges.exchange_dispatcher import ExchangeDispatcher
from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from trading.exchanges.rest_exchanges.rest_exchange import RESTExchange
from trading.exchanges.websockets_exchanges import AbstractWebSocket


class ExchangeManager:
    def __init__(self, config, exchange_type, is_simulated=False):
        self.config = config
        self.exchange_type = exchange_type
        self.logger = logging.getLogger(self.__class__.__name__)

        self.is_ready = False
        self.is_simulated = is_simulated

        self.exchange = None
        self.exchange_web_socket = None
        self.exchange_dispatcher = None

        self.client_symbols = []
        self.client_time_frames = []

        self.traded_pairs = []
        self.time_frames = []

        self.create_exchanges()

    def _load_constants(self):
        self._load_config_symbols_and_time_frames()
        self._set_config_time_frame()
        self._set_config_traded_pairs()

    def websocket_available(self):
        return self.exchange_web_socket

    def create_exchanges(self):
        if not self.is_simulated:
            # create REST based on ccxt exchange
            self.exchange = RESTExchange(self.config, self.exchange_type, self)

            self._load_constants()

            # create Websocket exchange if possible
            if self.check_web_socket_config(self.exchange.get_name()):
                for socket_manager in AbstractWebSocket.__subclasses__():
                    if socket_manager.get_name() == self.exchange.get_name():
                        self.exchange_web_socket = socket_manager.get_websocket_client(self.config, self)

                        # init websocket
                        self.exchange_web_socket.init_web_sockets(self.get_config_time_frame(), self.get_traded_pairs())

                        # start the websocket
                        self.exchange_web_socket.start_sockets()

        # if simulated : create exchange simulator instance
        else:
            self.exchange = ExchangeSimulator(self.config, self.exchange_type, self)

        self.exchange_dispatcher = ExchangeDispatcher(self.config, self.exchange_type,
                                                      self.exchange, self.exchange_web_socket)

        self.is_ready = True

    # should be used only in specific case
    def get_ccxt_exchange(self):
        return self.exchange

    def get_exchange(self):
        return self.exchange_dispatcher

    # Exchange configuration functions
    def check_config(self, exchange_name):
        if CONFIG_EXCHANGE_KEY not in self.config[CONFIG_EXCHANGES][exchange_name] \
                or CONFIG_EXCHANGE_SECRET not in self.config[CONFIG_EXCHANGES][exchange_name]:
            return False
        else:
            return True

    def check_web_socket_config(self, exchange_name):
        return self.check_config(exchange_name) \
               and CONFIG_EXCHANGE_WEB_SOCKET in self.config[CONFIG_EXCHANGES][exchange_name] \
               and self.config[CONFIG_EXCHANGES][exchange_name][CONFIG_EXCHANGE_WEB_SOCKET]

    def enabled(self):
        # if we can get candlestick data
        if self.is_simulated or self.exchange.get_name() in self.config[CONFIG_EXCHANGES]:
            return True
        else:
            self.logger.warning("Exchange {0} is currently disabled".format(self.exchange.get_name()))
            return False

    def _set_config_time_frame(self):
        for time_frame in TimeFrameManager.get_config_time_frame(self.config):
            if self.time_frame_exists(time_frame.value):
                self.time_frames.append(time_frame)
        # add shortest timeframe for realtime evaluators
        client_shortest_time_frame = TimeFrameManager.find_min_time_frame(self.client_time_frames, MIN_EVAL_TIME_FRAME)
        if client_shortest_time_frame not in self.time_frames:
            self.time_frames.append(client_shortest_time_frame)

    def get_config_time_frame(self):
        return self.time_frames

    def _set_config_traded_pairs(self):
        for cryptocurrency in self.config[CONFIG_CRYPTO_CURRENCIES]:
            for symbol in self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_PAIRS]:
                if self.symbol_exists(symbol):
                    self.traded_pairs.append(symbol)

    def get_traded_pairs(self):
        return self.traded_pairs

    def _load_config_symbols_and_time_frames(self):
        client = self.exchange.get_client()
        if client:
            self.client_symbols = client.symbols
            self.client_time_frames = client.timeframes
        else:
            self.logger.error("Failed to load client from REST exchange")
            self._raise_exchange_load_error()

    def symbol_exists(self, symbol):
        return symbol in self.client_symbols

    def time_frame_exists(self, time_frame):
        return time_frame in self.client_time_frames

    def get_client_symbols(self):
        return self.client_symbols

    def get_client_timeframes(self):
        return self.client_time_frames

    def get_rate_limit(self):
        return self.exchange_type.rateLimit / 1000

    # Getters
    def get_is_simulated(self):
        return self.is_simulated

    def get_symbol_data(self, symbol):
        return self.get_exchange().get_symbol_data(symbol)

    def get_personal_data(self):
        return self.get_exchange().get_exchange_personal_data()

    # Exceptions
    def _raise_exchange_load_error(self):
        raise Exception("{0} - Failed to load exchange instances".format(self.exchange))
