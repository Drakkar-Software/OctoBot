#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from tools.logging.logging_util import get_logger
import time

from config import CONFIG_TRADER, CONFIG_ENABLED_OPTION, CONFIG_EXCHANGES, CONFIG_EXCHANGE_KEY, \
    CONFIG_EXCHANGE_SECRET, CONFIG_CRYPTO_CURRENCIES, MIN_EVAL_TIME_FRAME, CONFIG_CRYPTO_PAIRS, \
    PriceIndexes, CONFIG_WILDCARD, CONFIG_EXCHANGE_WEB_SOCKET, CONFIG_CRYPTO_QUOTE, CONFIG_CRYPTO_ADD
from tools.symbol_util import split_symbol
from tools.time_frame_manager import TimeFrameManager
from tools.timestamp_util import is_valid_timestamp
from trading.exchanges.exchange_dispatcher import ExchangeDispatcher
from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from trading.exchanges.rest_exchanges.rest_exchange import RESTExchange
from trading.exchanges.websockets_exchanges import AbstractWebSocket
from tools.initializable import Initializable
from tools.config_manager import ConfigManager


class ExchangeManager(Initializable):
    WEB_SOCKET_RESET_MIN_INTERVAL = 15

    def __init__(self, config, exchange_type, is_simulated=False, rest_only=False, ignore_config=False):
        super().__init__()
        self.config = config
        self.exchange_type = exchange_type
        self.rest_only = rest_only
        self.ignore_config = ignore_config
        self.logger = get_logger(self.__class__.__name__)

        self.is_ready = False
        self.is_simulated = is_simulated

        self.exchange = None
        self.exchange_web_socket = None
        self.exchange_dispatcher = None
        self.trader = None

        self.last_web_socket_reset = None

        self.client_symbols = []
        self.client_time_frames = {}

        self.cryptocurrencies_traded_pairs = {}
        self.traded_pairs = []
        self.time_frames = []

    async def initialize_impl(self):
        await self.create_exchanges()

    def register_trader(self, trader):
        self.trader = trader

    def get_trader(self):
        return self.trader

    def _load_constants(self):
        self._load_config_symbols_and_time_frames()
        self._set_config_time_frame()
        self._set_config_traded_pairs()

    def websocket_available(self):
        return self.exchange_web_socket

    def need_user_stream(self):
        return self.config[CONFIG_TRADER][CONFIG_ENABLED_OPTION]

    async def create_exchanges(self):
        if not self.is_simulated:
            # create REST based on ccxt exchange
            self.exchange = RESTExchange(self.config, self.exchange_type, self)
            await self.exchange.initialize()

            self._load_constants()

            # create Websocket exchange if possible
            if not self.rest_only and self.check_web_socket_config(self.exchange.get_name()):
                for socket_manager in AbstractWebSocket.__subclasses__():
                    # add websocket exchange if available
                    if socket_manager.get_name() == self.exchange.get_name():
                        self.exchange_web_socket = socket_manager.get_websocket_client(self.config, self)

                        # init websocket
                        self.exchange_web_socket.init_web_sockets(self.get_config_time_frame(), self.traded_pairs)

                        # start the websocket
                        self.exchange_web_socket.start_sockets()

        # if simulated : create exchange simulator instance
        else:
            self.exchange = ExchangeSimulator(self.config, self.exchange_type, self)
            self._set_config_traded_pairs()

        self.exchange_dispatcher = ExchangeDispatcher(self.config, self.exchange_type,
                                                      self.exchange, self.exchange_web_socket)

        self.is_ready = True

    def did_not_just_try_to_reset_web_socket(self):
        if self.last_web_socket_reset is None:
            return True
        else:
            return time.time() - self.last_web_socket_reset > self.WEB_SOCKET_RESET_MIN_INTERVAL

    def reset_websocket_exchange(self):
        if self.exchange_web_socket and self.did_not_just_try_to_reset_web_socket():
            # set web socket reset time
            self.last_web_socket_reset = time.time()

            # clear databases
            self.exchange_dispatcher.reset_symbols_data()
            self.exchange_dispatcher.reset_exchange_personal_data()

            # close and restart websockets
            self.exchange_web_socket.close_and_restart_sockets()

            # databases will be filled at the next calls similarly to bot startup process

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

    def force_disable_web_socket(self, exchange_name):
        return CONFIG_EXCHANGE_WEB_SOCKET in self.config[CONFIG_EXCHANGES][exchange_name] \
               and not self.config[CONFIG_EXCHANGES][exchange_name][CONFIG_EXCHANGE_WEB_SOCKET]

    def check_web_socket_config(self, exchange_name):
        return self.check_config(exchange_name) and not self.force_disable_web_socket(exchange_name)

    def enabled(self):
        # if we can get candlestick data
        if self.is_simulated or self.exchange.get_name() in self.config[CONFIG_EXCHANGES]:
            return True
        else:
            self.logger.warning(f"Exchange {self.exchange.get_name()} is currently disabled")
            return False

    def get_exchange_symbol_id(self, symbol, with_fixer=False):
        return self.exchange.get_market_status(symbol, with_fixer=with_fixer)["id"]

    def _load_config_symbols_and_time_frames(self):
        client = self.exchange.get_client()
        if client:
            self.client_symbols = client.symbols
            self.client_time_frames[CONFIG_WILDCARD] = client.timeframes if hasattr(client, "timeframes") else {}
        else:
            self.logger.error("Failed to load client from REST exchange")
            self._raise_exchange_load_error()

    # SYMBOLS
    def _set_config_traded_pairs(self):
        self.cryptocurrencies_traded_pairs = {}
        for cryptocurrency in self.config[CONFIG_CRYPTO_CURRENCIES]:
            if self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_PAIRS]:
                if self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_PAIRS] != CONFIG_WILDCARD:
                    self.cryptocurrencies_traded_pairs[cryptocurrency] = []
                    for symbol in self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_PAIRS]:
                        if self.symbol_exists(symbol):
                            self.cryptocurrencies_traded_pairs[cryptocurrency].append(symbol)
                        else:
                            self.logger.error(f"{self.exchange.get_name()} is not supporting the "
                                              f"{symbol} trading pair.")

                else:
                    self.cryptocurrencies_traded_pairs[cryptocurrency] = self._create_wildcard_symbol_list(
                        self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_QUOTE])

                    # additionnal pairs
                    if CONFIG_CRYPTO_ADD in self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency]:
                        self.cryptocurrencies_traded_pairs[cryptocurrency] += self._add_tradable_symbols(cryptocurrency)

                # add to global traded pairs
                if not self.cryptocurrencies_traded_pairs[cryptocurrency]:
                    self.logger.error(f"{self.exchange.get_name()} is not supporting any {cryptocurrency} trading pair "
                                      f"from current configuration.")
                self.traded_pairs += self.cryptocurrencies_traded_pairs[cryptocurrency]
            else:
                self.logger.error(f"Current configuration for {cryptocurrency} is not including any trading pair, "
                                  f"this asset can't be traded and related orders won't be loaded. "
                                  f"OctoBot requires at least one trading pair in configuration to handle an asset. "
                                  f"You can add trading pair(s) for each asset in the configuration section.")

    def get_traded_pairs(self, cryptocurrency=None):
        if cryptocurrency:
            if cryptocurrency in self.cryptocurrencies_traded_pairs:
                return self.cryptocurrencies_traded_pairs[cryptocurrency]
            else:
                return []
        return self.traded_pairs

    def get_client_symbols(self):
        return self.client_symbols

    def symbol_exists(self, symbol):
        if self.client_symbols is None:
            self.logger.error(f"Failed to load available symbols from REST exchange, impossible to check if "
                              f"{symbol} exists on {self.exchange.get_name()}")
            return False
        return symbol in self.client_symbols

    def _create_wildcard_symbol_list(self, cryptocurrency):
        return [s for s in (self._is_tradable_with_cryptocurrency(symbol, cryptocurrency)
                            for symbol in self.client_symbols) if s is not None]

    def _add_tradable_symbols(self, cryptocurrency):
        return [
            symbol
            for symbol in self.config[CONFIG_CRYPTO_CURRENCIES][cryptocurrency][CONFIG_CRYPTO_ADD]
            if self.symbol_exists(symbol) and symbol not in self.cryptocurrencies_traded_pairs[cryptocurrency]
        ]

    @staticmethod
    def _is_tradable_with_cryptocurrency(symbol, cryptocurrency):
        return symbol if split_symbol(symbol)[1] == cryptocurrency else None

    # TIME FRAMES
    def _set_config_time_frame(self):
        for time_frame in TimeFrameManager.get_config_time_frame(self.config):
            if self.time_frame_exists(time_frame.value):
                self.time_frames.append(time_frame)
        # add shortest timeframe for realtime evaluators
        client_shortest_time_frame = TimeFrameManager.find_min_time_frame(
            self.client_time_frames[CONFIG_WILDCARD], MIN_EVAL_TIME_FRAME)
        if client_shortest_time_frame not in self.time_frames:
            self.time_frames.append(client_shortest_time_frame)

        self.time_frames = TimeFrameManager.sort_time_frames(self.time_frames, reverse=True)

    def get_config_time_frame(self):
        return self.time_frames

    def time_frame_exists(self, time_frame, symbol=None):
        if CONFIG_WILDCARD in self.client_time_frames or symbol is None:
            return time_frame in self.client_time_frames[CONFIG_WILDCARD]
        else:
            # should only happen in backtesting (or with an exchange with different timeframes per symbol)
            return time_frame in self.client_time_frames[symbol]

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

    @staticmethod
    def need_to_uniformize_timestamp(timestamp):
        return not is_valid_timestamp(timestamp)

    def uniformize_candles_if_necessary(self, candle_or_candles):
        if candle_or_candles:
            if isinstance(candle_or_candles[0], list):
                if self.need_to_uniformize_timestamp(candle_or_candles[0][PriceIndexes.IND_PRICE_TIME.value]):
                    self._uniformize_candles_timestamps(candle_or_candles)
            else:
                if self.need_to_uniformize_timestamp(candle_or_candles[PriceIndexes.IND_PRICE_TIME.value]):
                    self._uniformize_candle_timestamps(candle_or_candles)

    def _uniformize_candles_timestamps(self, candles):
        for candle in candles:
            self._uniformize_candle_timestamps(candle)

    def _uniformize_candle_timestamps(self, candle):
        candle[PriceIndexes.IND_PRICE_TIME.value] = \
            self.exchange_dispatcher.get_uniform_timestamp(candle[PriceIndexes.IND_PRICE_TIME.value])

    # Exceptions
    def _raise_exchange_load_error(self):
        raise Exception(f"{self.exchange} - Failed to load exchange instances")

    def get_exchange_name(self):
        return self.exchange_type.__name__

    def should_decrypt_token(self, logger):
        if ConfigManager.has_invalid_default_config_value(
                self.config[CONFIG_EXCHANGES][self.get_exchange_name()][CONFIG_EXCHANGE_KEY],
                self.config[CONFIG_EXCHANGES][self.get_exchange_name()][CONFIG_EXCHANGE_SECRET]):
            logger.warning("Exchange configuration tokens are not set yet, to use OctoBot's real trader's features, "
                           "please enter your api tokens in exchange configuration")
            return False
        return True

    @staticmethod
    def handle_token_error(error, logger):
        logger.error(f"Exchange configuration tokens are invalid : please check your configuration ! "
                     f"({error.__class__.__name__})")
