import logging

import pandas

from config.cst import *
from tools.time_frame_manager import TimeFrameManager
from trading.exchanges.rest_exchanges.rest_exchange import RESTExchange
from trading import WebSocketExchange
from trading.exchanges.exchange_dispatcher import ExchangeDispatcher
from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from trading.exchanges.websockets_exchanges import AbstractWebSocketManager


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

    def create_exchanges(self):
        if not self.is_simulated:
            # create REST based on ccxt exchange
            self.exchange = RESTExchange(self.config, self.exchange_type, self)

            self._load_constants()

            # create Websocket exchange if possible
            if self.check_web_socket_config(self.exchange.get_name()):
                for socket_manager in AbstractWebSocketManager.__subclasses__():
                    if socket_manager.get_name() == self.exchange.get_name():
                        self.exchange_web_socket = WebSocketExchange(self.config, self.exchange_type,
                                                                     self, socket_manager)
                        break

        # if simulated : create exchange simulator instance
        else:
            self.exchange = ExchangeSimulator(self.config, self.exchange_type, self)

        self.exchange_dispatcher = ExchangeDispatcher(self.config, self.exchange_type,
                                                      self.exchange, self.exchange_web_socket)

        self.is_ready = True

    def get_exchange(self):
        return self.exchange_dispatcher

    # Exchange configuration functions
    def check_config(self, exchange_name):
        if not self.config[CONFIG_EXCHANGES][exchange_name][CONFIG_EXCHANGE_KEY] \
                and not self.config[CONFIG_EXCHANGES][exchange_name][CONFIG_EXCHANGE_SECRET]:
            return False
        else:
            return True

    def check_web_socket_config(self, exchange_name):
        if CONFIG_EXCHANGE_WEB_SOCKET in self.config[CONFIG_EXCHANGES][exchange_name] \
                and self.config[CONFIG_EXCHANGES][exchange_name][CONFIG_EXCHANGE_WEB_SOCKET]:
            return True
        else:
            return False

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
        if symbol in self.client_symbols:
            return True
        else:
            return False

    def time_frame_exists(self, time_frame):
        if time_frame in self.client_time_frames:
            return True
        else:
            return False

    def get_client_symbols(self):
        return self.client_symbols

    def get_client_timeframes(self):
        return self.client_time_frames

    def get_rate_limit(self):
        return self.exchange_type.rateLimit / 1000

    # Candles
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

    # Getters
    def get_is_simulated(self):
        return self.is_simulated

    # Exceptions
    def _raise_exchange_load_error(self):
        raise Exception("{0} - Failed to load exchange instances")
