#  Drakkar-Software OctoBot-Trading
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
import typing
import uuid

import octobot_commons.configuration as configuration
import octobot_commons.constants as common_constants
import octobot_commons.logging as logging
import octobot_commons.timestamp_util as timestamp_util

import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.exchanges as exchanges
import octobot_trading.personal_data as personal_data
import octobot_trading.exchange_data as exchange_data
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.util as util
import octobot_trading.errors as errors
import octobot_trading.storage as storage
import octobot_trading.exchanges.config.exchange_credentials_data as exchange_credentials_data
import trading_backend.exchanges


class ExchangeManager(util.Initializable):
    def __init__(self, config, exchange_class_string):
        super().__init__()
        self.id: str = str(uuid.uuid4())
        self.bot_id: str = None  # type: ignore
        self.config: dict = config
        self.tentacles_setup_config = None
        self.exchange_class_string: str = exchange_class_string
        self.exchange_name: str = exchange_class_string
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)

        self.is_ready: bool = False
        self.is_simulated: bool = False
        self.is_backtesting: bool = False
        self.rest_only: bool = False
        self.ignore_config: bool = False
        self.use_cached_markets: bool = True
        self.market_filter: typing.Union[None, typing.Callable[[dict], bool]] = None
        self.is_spot_only: bool = False
        self.is_margin: bool = False
        self.is_future: bool = False
        self.is_option: bool = False
        self.is_sandboxed: bool = False
        self.is_trading: bool = True
        self.without_auth: bool = False
        self.disable_unauth_retry: bool = False
        self.check_credentials: bool = True
        self.enable_storage: bool = True
        self.proxy_config: exchanges.ProxyConfig = exchanges.ProxyConfig.default_env_var_config()

        # exchange_only is True when exchange channels are not required (therefore not created)
        self.exchange_only: bool = False

        self.backtesting = None

        self.is_trader_simulated: bool = util.is_trader_simulator_enabled(self.config)
        self.has_websocket: bool = False

        self.trader: exchanges.Trader = None # type: ignore
        self.exchange: exchanges.RestExchange = None # type: ignore
        self.preconfigured_exchange: typing.Optional[exchanges.RestExchange] = None
        self.leave_rest_exchange_open: bool = False
        self.exchange_backend: trading_backend.exchanges.Exchange = None # type: ignore
        self.is_broker_enabled: bool = False
        self.trading_modes: list = []

        self.exchange_web_socket: typing.Optional[exchanges.WebSocketExchange] = None

        self.client_symbols: list[str] = []
        self.client_time_frames: list[str] = []

        self.storage_manager: storage.StorageManager = storage.StorageManager(self)
        self.exchange_config: exchanges.ExchangeConfig = exchanges.ExchangeConfig(self)
        self.exchange_personal_data: personal_data.ExchangePersonalData = personal_data.ExchangePersonalData(self)
        self.exchange_symbols_data: exchange_data.ExchangeSymbolsData = exchange_data.ExchangeSymbolsData(self)

        self.debug_info: dict[str, typing.Any] = {}

    async def initialize_impl(self, exchange_config_by_exchange: typing.Optional[dict[str, dict]]):
        await exchanges.create_exchanges(self, exchange_config_by_exchange)
        if self.is_storage_enabled():
            await self.storage_manager.initialize()

    async def stop(self, warning_on_missing_elements=True, enable_logs=True):
        """
        Stops exchange manager relative tasks : websockets, trading mode, and exchange channels
        :param warning_on_missing_elements: warn on missing element
        :param enable_logs: log stopping steps
        """
        if enable_logs:
            self.logger.debug("Stopping ...")
        # stop websockets if any
        if self.has_websocket:
            if enable_logs:
                self.logger.debug("Stopping websocket ...")
            try:
                await self.exchange_web_socket.stop_sockets()
                await self.exchange_web_socket.close_sockets()
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping exchange websocket: {err}")
            if enable_logs:
                self.logger.debug("Stopped websocket")
        if self.exchange_web_socket:
            self.exchange_web_socket.clear()
            self.exchange_web_socket = None

        # stop trading modes
        if enable_logs:
            self.logger.debug("Stopping trading modes ...")
        for trading_mode in self.trading_modes:
            try:
                await trading_mode.stop()
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping trading mode: {err}")
        if enable_logs:
            self.logger.debug("Stopped trading modes")

        # stop exchange channels
        if enable_logs:
            self.logger.debug(f"Stopping exchange channels for exchange_id: {self.id} ...")
        if self.exchange is not None and not self.leave_rest_exchange_open:
            try:
                exchange_channel.get_exchange_channels(self.id)
                await exchange_channel.stop_exchange_channels(self, should_warn=warning_on_missing_elements)
            except KeyError:
                # no exchange channel to stop
                pass
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping exchange channels: {err}")
            try:
                await self.exchange.stop()
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping exchange: {err}")
            if self.exchange is not None:
                # ensure self.exchange still exists as await self.exchange.stop()
                # internally uses asyncio.sleep within ccxt
                exchanges.Exchanges.instance().del_exchange(
                    self.exchange.name, self.id, should_warn=warning_on_missing_elements
                )
                self.exchange.exchange_manager = None # type: ignore
            self.exchange = None # type: ignore
        if self.exchange_personal_data is not None:
            try:
                await self.exchange_personal_data.stop()
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping exchange_personal_data: {err}")
        if self.exchange_symbols_data is not None:
            try:
                await self.exchange_symbols_data.stop()
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping exchange_symbols_data: {err}")
        if enable_logs:
            self.logger.debug(f"Stopped exchange channels for exchange_id: {self.id}")

        if enable_logs:
            self.logger.debug("Stopping storages ...")
        try:
            await self.storage_manager.stop()
        except Exception as err:
            self.logger.exception(err, True, f"Error when stopping storage_manager: {err}")

        if self.proxy_config and self.proxy_config.stop_proxy_callback is not None:
            try:
                self.proxy_config.stop_proxy_callback()
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping proxy: {err}")

        self.exchange_config = None # type: ignore
        self.exchange_personal_data = None # type: ignore
        self.exchange_symbols_data = None # type: ignore
        if self.exchange_backend is not None:
            try:
                self.exchange_backend.stop()
            except Exception as err:
                self.logger.exception(err, True, f"Error when stopping exchange_backend: {err}")
        if enable_logs:
            self.logger.debug("Stopping trader ...")
        if self.trader is not None:
            self.trader.clear()
            self.trader = None # type: ignore
        if enable_logs:
            self.logger.debug("Stopped trader")
        self.trading_modes = []
        self.backtesting = None # type: ignore
        if enable_logs:
            self.logger.debug("Stopped")

    async def register_trader(self, trader):
        self.trader = trader
        await self.exchange_personal_data.initialize()
        await self.exchange_config.initialize()

    def load_constants(self):
        if not self.is_backtesting:
            self._load_config_symbols_and_time_frames()
            self.exchange_config.set_config_time_frame()
            self.exchange_config.set_config_traded_pairs()
        # always call set_historical_settings
        self.exchange_config.set_historical_settings()
        if not self.exchange_only:
            self.exchange_config.initialize_exchange_event_tree()

    def need_user_stream(self):
        return self.config[common_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION]

    def reset_exchange_symbols_data(self):
        self.exchange_symbols_data = exchange_data.ExchangeSymbolsData(self)

    def reset_exchange_personal_data(self):
        self.exchange_personal_data = personal_data.ExchangePersonalData(self)

    """
    Exchange Configuration
    """

    def check_config(self, exchange_name):
        if common_constants.CONFIG_EXCHANGE_KEY not in self.config[common_constants.CONFIG_EXCHANGES][exchange_name] \
                or common_constants.CONFIG_EXCHANGE_SECRET not in self.config[common_constants.CONFIG_EXCHANGES][exchange_name]:
            return False
        else:
            return True

    def enabled(self):
        # if we can get candlestick data
        if self.is_simulated or self.exchange.name in self.config[common_constants.CONFIG_EXCHANGES]:
            return True
        else:
            self.logger.warning(f"Exchange {self.exchange.name} is currently disabled")
            return False

    def get_exchange_symbol(self, symbol):
        return self.exchange.get_pair_from_exchange(symbol)

    def get_exchange_quote_and_base(self, symbol):
        return self.exchange.get_split_pair_from_exchange(symbol)

    def get_symbol_data(self, symbol):
        return self.exchange_symbols_data.get_exchange_symbol_data(symbol)

    def get_rest_pairs_refresh_threshold(self) -> enums.RestExchangePairsRefreshMaxThresholds:
        traded_pairs_count = len(self.exchange_config.traded_symbol_pairs) + len(self.exchange_config.additional_traded_pairs)
        if traded_pairs_count < enums.RestExchangePairsRefreshMaxThresholds.FAST.value:
            return enums.RestExchangePairsRefreshMaxThresholds.FAST
        if traded_pairs_count < enums.RestExchangePairsRefreshMaxThresholds.MEDIUM.value:
            return enums.RestExchangePairsRefreshMaxThresholds.MEDIUM
        return enums.RestExchangePairsRefreshMaxThresholds.SLOW

    def _load_config_symbols_and_time_frames(self):
        if self.exchange.symbols and self.exchange.time_frames:
            self.client_symbols = list(self.exchange.symbols)
            self.client_time_frames = list(self.exchange.time_frames)
        elif not self.exchange_only:
            err_message = "Failed to load exchange symbols or time frames"
            self.logger.error(err_message)
            self._raise_exchange_load_error(err_message)

    def symbol_exists(self, symbol):
        if self.client_symbols is None:
            self.logger.error(f"Failed to load available symbols from REST exchange, impossible to check if "
                              f"{symbol} exists on {self.exchange.name}")
            return False
        return symbol in self.client_symbols

    def time_frame_exists(self, time_frame):
        if not self.client_time_frames:
            return False
        return time_frame in self.client_time_frames

    # Exceptions
    def _raise_exchange_load_error(self, desc):
        raise Exception(f"{self.exchange} - Failed to load exchange instances: {desc}")

    def get_exchange_name(self):
        return self.exchange_class_string

    def get_currently_handled_pair_with_time_frame(self):
        return len(self.exchange_config.traded_symbol_pairs) * len(self.exchange_config.available_time_frames)

    def ensure_reachability(self):
        """
        Raises UnreachableExchange if the exchange is not available
        Warning: only working in backtesting for now as self.exchange.is_unreachable
        is not updated in live mode
        """
        if self.exchange.is_unreachable:
            current_time = self.exchange.get_exchange_current_time()
            raise errors.UnreachableExchange(f"{self.exchange_name} can't be reached or is offline on the "
                                             f"{timestamp_util.convert_timestamp_to_datetime(current_time)} "
                                             f"(timestamp: {current_time})")

    def get_is_overloaded(self):
        if self.has_websocket:
            return False
        max_handled = self.exchange.get_max_handled_pair_with_time_frame()
        return max_handled != constants.INFINITE_MAX_HANDLED_PAIRS_WITH_TIMEFRAME and max_handled < \
            self.get_currently_handled_pair_with_time_frame()

    def should_decrypt_token(self):
        if configuration.has_invalid_default_config_value(
                self.config[common_constants.CONFIG_EXCHANGES][self.get_exchange_name()].get(
                    common_constants.CONFIG_EXCHANGE_KEY, ''),
                self.config[common_constants.CONFIG_EXCHANGES][self.get_exchange_name()].get(
                    common_constants.CONFIG_EXCHANGE_SECRET, '')):
            return False
        return True

    def get_exchange_credentials(self, exchange_name) -> exchange_credentials_data.ExchangeCredentialsData:
        creds = exchange_credentials_data.ExchangeCredentialsData()
        if self.ignore_config or not self.should_decrypt_token() or self.without_auth:
            return creds
        config_exchange = self.config[common_constants.CONFIG_EXCHANGES][exchange_name]
        key = configuration.decrypt_element_if_possible(
            common_constants.CONFIG_EXCHANGE_KEY, config_exchange, None
        )
        secret = configuration.decrypt_element_if_possible(
            common_constants.CONFIG_EXCHANGE_SECRET, config_exchange, None
        )
        # remove leading and trailing ", ', newlines and whitespaces if any
        creds.api_key = key.strip(' "').strip("'").strip("\n") if key else key
        creds.secret = secret.strip(' "').strip("'").strip("\n") if secret else secret
        creds.password = configuration.decrypt_element_if_possible(
            common_constants.CONFIG_EXCHANGE_PASSWORD, config_exchange, None
        )
        creds.uid = config_exchange.get(common_constants.CONFIG_EXCHANGE_UID, "")
        creds.auth_token = config_exchange.get(common_constants.CONFIG_EXCHANGE_ACCESS_TOKEN, "")
        return creds

    def get_exchange_sub_account_id(self, exchange_name):
        config_exchange = self.config[common_constants.CONFIG_EXCHANGES][exchange_name]
        return config_exchange.get(common_constants.CONFIG_EXCHANGE_SUB_ACCOUNT, None)

    def is_storage_enabled(self):
        return self.enable_storage and not self.exchange_only and self.bot_id is not None

    def update_debug_info(self):
        self.debug_info = {
            "str": str(self),
            "trading_modes": str([tm.get_name() for tm in self.trading_modes]),
            "available_time_frames": str(self.exchange_config.available_time_frames),
            "watched_pairs": str(self.exchange_config.watched_pairs),
            "traded_symbol_pairs": str(self.exchange_config.traded_symbol_pairs),
        }

    def __str__(self):
        exchange_type = 'rest'
        exchange_type = 'spot only' if self.is_spot_only else exchange_type
        exchange_type = 'margin' if self.is_margin else exchange_type
        exchange_type = 'future' if self.is_future else exchange_type
        exchange_type = 'option' if self.is_option else exchange_type
        return f"[{self.__class__.__name__}] with {self.exchange.__class__.__name__ if self.exchange else '?'} " \
               f"exchange class on {self.get_exchange_name()} | {exchange_type} | " \
               f"{'authenticated | ' if self.exchange and self.exchange.authenticated() else 'unauthenticated | '}" \
               f"{'backtesting | ' if self.backtesting else ''}{'sandboxed | ' if self.is_sandboxed else ''}" \
               f"{'' if self.is_trading else 'not trading | '}" \
               f"{'websocket | ' if self.has_websocket else 'no websocket | '} id: {self.id}"
