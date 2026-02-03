# cython: language_level=3
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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import typing
import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants
import octobot_commons.authentication as commons_authentication

import octobot_trading.errors as errors
import octobot_trading.modes as modes
import octobot_trading.exchanges as exchanges
import octobot_trading.constants as constants
import octobot_trading.util as util


class ExchangeBuilder:
    def __init__(self, config, exchange_name):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.config: dict = config
        self.exchange_name: str = exchange_name

        self.exchange_manager: exchanges.ExchangeManager = exchanges.ExchangeManager(self.config, self.exchange_name)

        self._is_using_trading_modes: bool = True
        self._matrix_id: str = None
        self.trading_config_by_trading_mode: dict = None
        self.exchange_config_by_exchange: dict = None
        self.auto_start_trading_modes: bool = True

    async def build(self):
        """
        Build the exchange
        """
        try:
            await self._build_exchange_manager()
        except Exception as e:
            # stop exchange manager if an exception occurred when building it
            await self.exchange_manager.stop(warning_on_missing_elements=False)
            raise e
        return self.exchange_manager

    def clear(self):
        self.exchange_manager = None

    async def _build_exchange_manager(self):
        trading_mode_class = None

        try:
            if self._is_using_trading_modes:
                trading_mode_class = modes.get_activated_trading_mode(self.exchange_manager.tentacles_setup_config)
                # handle exchange related requirements if the activated trading mode has any
                await self._register_trading_modes_requirements(
                    trading_mode_class, self.exchange_manager.tentacles_setup_config
                )

            self._ensure_exchange_compatibility()
            await self.exchange_manager.initialize(exchange_config_by_exchange=self.exchange_config_by_exchange)
            # add exchange to be able to use it
            exchanges.Exchanges.instance().add_exchange(self.exchange_manager, self._matrix_id)

            # initialize exchange for trading if not collecting
            if not self.exchange_manager.exchange_only:

                # initialize trader
                if self.exchange_manager.trader is not None:
                    await self._build_trader()

                # create trading modes
                await self._build_trading_modes_if_required(
                    trading_mode_class, self.exchange_manager.tentacles_setup_config
                )

            # add to global exchanges
            self.exchange_manager.update_debug_info()
        except Exception:
            exchanges.Exchanges.instance().del_exchange(
                self.exchange_manager.exchange_name, self.exchange_manager.id, should_warn=False
            )
            raise

    async def _build_trader(self):
        try:
            # check traders activation
            if not util.is_trader_enabled(self.config) and not util.is_trader_simulator_enabled(self.config):
                raise ValueError(f"No trader simulator nor real trader activated on "
                                 f"{self.exchange_manager.exchange_name}")

            await self.exchange_manager.trader.initialize()
        except ValueError as e:
            self.logger.error(f"An error occurred when creating trader : {e}")
            raise e

    async def _register_trading_modes_requirements(self, trading_mode_class, tentacles_setup_config):
        self.exchange_manager.is_trading = trading_mode_class.get_is_trading_on_exchange(
            self.exchange_name, tentacles_setup_config
        )
        if not self.exchange_manager.is_trading:
            self.logger.info(
                f"{self.exchange_manager.exchange_name} exchange is configured not to apply any trading strategy."
            )
        # take trading modes candles requirements into account if any
        self.config[commons_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT] = max(
            self.config[commons_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT],
            modes.get_required_candles_count(trading_mode_class, tentacles_setup_config)
        )
        self.exchange_manager.exchange_config.set_is_saving_cancelled_orders_as_trade(
            not trading_mode_class.is_ignoring_cancelled_orders_trades()
        )

    async def _build_trading_modes_if_required(self, trading_mode_class, tentacles_setup_config):
        if self._is_using_trading_modes:
            # self.exchange_manager.trader can be None if neither simulator or real trader has be set
            if self.exchange_manager.is_trading and (
                self.exchange_manager.trader is None or (
                    trading_mode_class.get_is_using_trading_mode_on_exchange(
                        self.exchange_name, tentacles_setup_config
                    )
                )
            ):
                if self.exchange_manager.trader is None:
                    self.logger.warning(f"There wont be any order created on {self.exchange_name}: neither "
                                        f"simulated nor real trader has been activated.")
                else:
                    self.exchange_manager.trading_modes = await self.build_trading_modes(trading_mode_class)
            else:
                no_action = "trading without using direct trading mode" if self.exchange_manager.is_trading else "trading"
                self.logger.info(f"{self.exchange_name} exchange is online and won't be {no_action}")

    async def build_trading_modes(self, trading_mode_class):
        try:
            # ensure authenticated data are fetched before starting trading modes
            if not self.exchange_manager.is_backtesting:
                await commons_authentication.Authenticator.wait_and_check_has_open_source_package()
            self._ensure_trading_mode_compatibility(trading_mode_class)
            return await modes.create_trading_modes(
                self.config,
                self.exchange_manager,
                trading_mode_class,
                self.exchange_manager.bot_id,
                trading_config_by_trading_mode=self.trading_config_by_trading_mode,
                auto_start=self.auto_start_trading_modes,
            )
        except errors.TradingModeIncompatibility as e:
            raise e
        except Exception as e:
            self.logger.error(f"An error occurred when initializing trading mode : {e}")
            raise e

    def _ensure_exchange_compatibility(self):
        if self.exchange_manager.is_backtesting or self.exchange_manager.exchange_only:
            # allow backtesting and collecting on incompatible exchange types
            return
        # live exchange: ensure the exchange to be created supports the trading type
        supported_exchange_types = exchanges.get_supported_exchange_types(
            self.exchange_manager.exchange_name,
            self.exchange_manager.tentacles_setup_config
        )
        exchange_type = exchanges.get_exchange_type(self.exchange_manager)
        if exchange_type not in supported_exchange_types:
            raise errors.NotSupported(f"{self.exchange_manager.exchange_name} does not support {exchange_type.value}"
                                      f" trading. "
                                      f"Supported exchange types are {[t.value for t in supported_exchange_types]}.")

    def _ensure_trading_mode_compatibility(self, trading_mode_class):
        to_check_exchange_type = exchanges.get_exchange_type(self.exchange_manager)
        if to_check_exchange_type not in trading_mode_class.get_supported_exchange_types():
            self.logger.error(f"{trading_mode_class.get_name()} is not compatible with a {to_check_exchange_type.value} "
                              f"exchange. Activating it might have unexpected effects.")
        # raise errors.TradingModeIncompatibility if we decide we need to prevent the trading mode creation

    """
    Builder methods
    """

    def is_backtesting(self, backtesting_instance):
        self.exchange_manager.is_backtesting = True
        self.exchange_manager.exchange_config.init_backtesting_exchange_config()
        self.exchange_manager.backtesting = backtesting_instance
        return self

    def is_sandboxed(self, sandboxed: bool):
        self.exchange_manager.is_sandboxed = sandboxed
        return self

    def is_simulated(self):
        self.exchange_manager.is_simulated = True
        self.exchange_manager.trader = exchanges.TraderSimulator(self.config, self.exchange_manager)
        return self

    def is_real(self):
        self.exchange_manager.is_simulated = False
        self.exchange_manager.trader = exchanges.Trader(self.config, self.exchange_manager)
        return self

    def is_using_exchange_type(self, exchange_type):
        if exchange_type == commons_constants.CONFIG_EXCHANGE_FUTURE:
            self.is_future(True)
        elif exchange_type == commons_constants.CONFIG_EXCHANGE_MARGIN:
            self.is_margin(True)
        elif exchange_type == commons_constants.CONFIG_EXCHANGE_OPTION:
            self.is_option(True)
        else:
            # Use spot trading as default trading type
            self.is_spot_only(True)
        return self

    def is_margin(self, use_margin=True):
        self.exchange_manager.is_margin = use_margin
        return self

    def is_future(self, use_future=True, future_contract_type=constants.DEFAULT_SYMBOL_FUTURE_CONTRACT_TYPE):
        self.exchange_manager.is_future = use_future
        if self.exchange_manager.is_backtesting:
            self.exchange_manager.exchange_config.backtesting_exchange_config.future_contract_type = \
                future_contract_type
        return self

    def is_option(self, use_option=True, option_contract_type=constants.DEFAULT_SYMBOL_OPTION_CONTRACT_TYPE):
        self.exchange_manager.is_option = use_option
        if self.exchange_manager.is_backtesting:
            self.exchange_manager.exchange_config.backtesting_exchange_config.option_contract_type = \
                option_contract_type
        return self

    def enable_storage(self, enabled):
        self.exchange_manager.enable_storage = enabled
        return self

    def is_spot_only(self, use_spot_only=True):
        self.exchange_manager.is_spot_only = use_spot_only
        return self

    def is_rest_only(self):
        self.exchange_manager.rest_only = True
        return self

    def is_exchange_only(self):
        self.exchange_manager.exchange_only = True
        return self

    def use_cached_markets(self, use_cached_markets: bool):
        self.exchange_manager.use_cached_markets = use_cached_markets
        return self

    def use_market_filter(self, market_filter: typing.Union[None, typing.Callable[[dict], bool]]):
        self.exchange_manager.market_filter = market_filter
        return self

    def set_rest_exchange(self, rest_exchange: typing.Optional["exchanges.RestExchange"]):
        self.exchange_manager.preconfigured_exchange = rest_exchange
        return self

    def leave_rest_exchange_open(self, leave_rest_exchange_open: bool):
        self.exchange_manager.leave_rest_exchange_open = leave_rest_exchange_open
        return self
    
    def is_ignoring_config(self, ignore_config=True):
        self.exchange_manager.ignore_config = ignore_config
        return self

    def is_broker_enabled(self, is_broker_enabled=False):
        self.exchange_manager.is_broker_enabled = is_broker_enabled
        return self

    def is_without_auth(self):
        self.exchange_manager.without_auth = True
        return self

    def disable_unauth_retry(self, disabled):
        self.exchange_manager.disable_unauth_retry = disabled
        return self

    def is_checking_credentials(self, check_credentials):
        self.exchange_manager.check_credentials = check_credentials
        return self

    def use_tentacles_setup_config(self, tentacles_setup_config):
        self.exchange_manager.tentacles_setup_config = tentacles_setup_config
        return self

    def set_bot_id(self, bot_id):
        self.exchange_manager.bot_id = bot_id
        return self

    def set_proxy_config(self, proxy_config):
        self.exchange_manager.proxy_config = proxy_config
        return self

    def disable_trading_mode(self):
        self._is_using_trading_modes = False
        return self

    def has_matrix(self, matrix_id):
        self._matrix_id = matrix_id
        return self

    def use_trading_config_by_trading_mode(self, trading_config_by_trading_mode):
        self.trading_config_by_trading_mode = trading_config_by_trading_mode
        return self

    def use_exchange_config_by_exchange(self, exchange_config_by_exchange: typing.Optional[dict[str, dict]]):
        self.exchange_config_by_exchange = exchange_config_by_exchange
        return self

    def set_auto_start_trading_modes(self, auto_start_trading_modes):
        self.auto_start_trading_modes = auto_start_trading_modes
        return self

    def enable_realtime_data_fetching(self, enabled: bool = True):
        self.exchange_manager.exchange_config.realtime_data_fetching = enabled
        return self


def create_exchange_builder_instance(config, exchange_name):
    return ExchangeBuilder(config, exchange_name)
