import pandas

from config.cst import *
from trading.exchanges.abstract_exchange import AbstractExchange
from trading.exchanges.websockets import AbstractWebSocketManager


class ExchangeManager(AbstractExchange):
    def __init__(self, exchange_type):
        super().__init__(exchange_type)

        self.is_ready = False
        self.is_simulated = False

        self.client_symbols = []
        self.client_time_frames = []

        self.config = None
        self.exchange_type = None

        self.name = self.exchange_type.__name__
        self.traded_pairs = []
        self.time_frames = []

    def set_config(self, config, exchange_type):
        self.config = config
        self.exchange_type = exchange_type

    def _load_constants(self):
        self._load_config_symbols_and_time_frames()
        self._set_config_time_frame()
        self._set_config_traded_pairs()

    def create_exchanges(self):
        if not self.is_simulated:
            # create REST based on ccxt exchange
            self.exchange = self.exchange_type()

            # create Websocket exchange if possible
            # check if websocket is available for this exchange
            for socket_manager in AbstractWebSocketManager.__subclasses__():
                if socket_manager.get_name() == self.get_name().lower():
                    self.exchange_web_socket = socket_manager.get_websocket_client(self.config)

            # if a Websocket instance is created
            if self.exchange_web_socket:

                # init websocket
                self.exchange_web_socket.init_web_sockets()

                # start the websocket
                self.exchange_web_socket.start_sockets()

            self._load_constants()

        self.is_ready = True

    # Exchange configuration functions
    def check_config(self):
        if not self.config["exchanges"][self.name]["api-key"] \
                and not self.config["exchanges"][self.name]["api-secret"]:
            return False
        else:
            return True

    def enabled(self):
        # if we can get candlestick data
        if self.is_simulated or self.name in self.config[CONFIG_EXCHANGES]:
            return True
        else:
            self.logger.warning("Exchange {0} is currently disabled".format(self.name))
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
    def get_name(self):
        return self.name

    def get_is_simulated(self):
        return self.is_simulated

    # Exceptions
    def _raise_exchange_load_error(self):
        raise Exception("{0} - Failed to load exchange instances")

