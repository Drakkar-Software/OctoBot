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

import ccxt.async_support as ccxt

from backtesting import backtesting_enabled
from config import CONFIG_EXCHANGES
from evaluator.Updaters.global_price_updater import GlobalPriceUpdater
from tools.logging.logging_util import get_logger
from trading.exchanges.exchange_manager import ExchangeManager
from trading.trader.previous_trading_state_manager import PreviousTradingStateManager
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator
from trading.util.trading_config_util import get_activated_trading_mode


class ExchangeFactory:
    """ExchangeFactory class:
    - Create exchanges and trades according to configureated exchanges
    """

    def __init__(self, octobot, ignore_config=False):
        self.octobot = octobot
        self.ignore_config = ignore_config

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.exchange_traders = {}
        self.exchange_trader_simulators = {}
        self.exchange_trading_modes = {}
        self.trading_mode = None
        self.previous_trading_state_manager = None
        self.exchanges_list = {}
        self.global_updaters_by_exchange = {}

        self.available_exchanges = ccxt.exchanges

    async def create(self):
        self.create_previous_state_manager()

        if self.octobot.get_config()[CONFIG_EXCHANGES]:
            for exchange_class_string in self.octobot.get_config()[CONFIG_EXCHANGES]:
                if exchange_class_string in self.available_exchanges:
                    await self._create_exchange_traders(exchange_class_string)
                else:
                    self.logger.error(f"{exchange_class_string} exchange not found")
        else:
            self.logger.error("No exchange in configuration. OctoBot requires at least one exchange "
                              "to read trading data from. You can add exchanges in the configuration section.")

    def create_previous_state_manager(self):
        if not backtesting_enabled(self.octobot.get_config()) and \
                PreviousTradingStateManager.enabled(self.octobot.get_config()):

            self.previous_trading_state_manager = PreviousTradingStateManager(
                self.octobot.get_config()[CONFIG_EXCHANGES],
                self.octobot.reset_trading_history,
                self.octobot.get_config()
            )

    async def _create_exchange_traders(self, exchange_class_string):
        # create exchange manager (can be a backtesting or a real one)
        exchange_manager = self._create_exchange_manager(getattr(ccxt, exchange_class_string))

        await exchange_manager.initialize()

        exchange_inst = self._create_exchange_instances(exchange_manager)

        self._create_global_price_updater(exchange_inst)

        await self._create_traders(exchange_inst)

        # check traders activation
        if not self._is_minimum_traders_activated(exchange_inst):
            self.logger.error(f"No trader simulator nor real trader activated on {exchange_inst.get_name()}")

        self._create_trading_mode(exchange_inst)

        self.register_trading_mode_on_traders(exchange_inst)

    def _create_exchange_instances(self, exchange_manager):
        exchange_inst = exchange_manager.get_exchange()
        self.exchanges_list[exchange_inst.get_name()] = exchange_inst
        return exchange_inst

    def _create_global_price_updater(self, exchange_inst) -> None:
        self.global_updaters_by_exchange[exchange_inst.get_name()] = GlobalPriceUpdater(exchange_inst)

    def _create_exchange_manager(self, exchange_type) -> ExchangeManager:
        # Backtesting Exchange
        if backtesting_enabled(self.octobot.get_config()):
            return ExchangeManager(self.octobot.get_config(), exchange_type, is_simulated=True)
        else:
            # Real Exchange
            return ExchangeManager(self.octobot.get_config(), exchange_type, ignore_config=self.ignore_config)

    async def _create_trader(self, trader_class, exchange_inst) -> Trader:
        exchange_trader = trader_class(self.octobot.get_config(), exchange_inst,
                                       previous_state_manager=self.previous_trading_state_manager)
        await exchange_trader.initialize()
        return exchange_trader

    # create trader & trader simulator instance for this exchange
    async def _create_traders(self, exchange_inst) -> None:
        self.exchange_traders[exchange_inst.get_name()] = await self._create_trader(Trader, exchange_inst)
        self.exchange_trader_simulators[exchange_inst.get_name()] = await self._create_trader(TraderSimulator,
                                                                                              exchange_inst)

    def _is_minimum_traders_activated(self, exchange_inst) -> bool:
        return self.exchange_traders[exchange_inst.get_name()].enabled(self.octobot.get_config()) or \
               self.exchange_trader_simulators[exchange_inst.get_name()].enabled(self.octobot.get_config())

    def _create_trading_mode(self, exchange_inst) -> None:
        try:
            self.trading_mode = get_activated_trading_mode(self.octobot.get_config())(self.octobot.get_config(),
                                                                                      exchange_inst)
            self.exchange_trading_modes[exchange_inst.get_name()] = self.trading_mode
            self.logger.debug(f"Using {self.trading_mode.get_name()} trading mode")
        except RuntimeError as e:
            self.logger.error(e.args[0])
            raise e

    def _register_trading_mode_with_trader(self, trader) -> None:
        trader.register_trading_mode(self.trading_mode)

    def register_trading_mode_on_traders(self, exchange_inst) -> None:
        self._register_trading_mode_with_trader(self.exchange_traders[exchange_inst.get_name()])
        self._register_trading_mode_with_trader(self.exchange_trader_simulators[exchange_inst.get_name()])
