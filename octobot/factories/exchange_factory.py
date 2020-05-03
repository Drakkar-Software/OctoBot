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
import ccxt

from octobot.api.backtesting import create_independent_backtesting, initialize_and_run_independent_backtesting
from octobot.backtesting.independent_backtesting import IndependentBacktesting
from octobot_backtesting.api.backtesting import is_backtesting_enabled, get_backtesting_data_files, \
    initialize_backtesting, adapt_backtesting_channels, start_backtesting
from octobot_backtesting.importers.exchanges.exchange_importer import ExchangeDataImporter
from octobot_commons.logging.logging_util import get_logger
from octobot_trading.api.exchange import create_exchange_builder
from octobot_trading.api.trader import is_trader_enabled_in_config, is_trader_simulator_enabled_in_config
from octobot_trading.constants import CONFIG_EXCHANGES
from octobot.logger import init_exchange_chan_logger


class ExchangeFactory:
    """
    - Create exchanges and trades according to configured exchanges
    """

    def __init__(self, octobot, ignore_config=False):
        self.octobot = octobot
        self.ignore_config = ignore_config

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.exchange_manager = None
        self.exchange_manager_ids = []
        self.exchange_traders = {}
        self.exchange_trader_simulators = {}
        self.exchange_trading_modes = {}
        self.trading_mode = None
        self.previous_trading_state_manager = None
        self.exchanges_list = {}
        self.global_updaters_by_exchange = {}

        self.available_exchanges = ccxt.exchanges

    async def _create_exchanges(self, backtesting=None):
        for exchange_class_string in self.octobot.config[CONFIG_EXCHANGES]:
            if exchange_class_string in self.available_exchanges:
                exchange_builder = create_exchange_builder(self.octobot.config, exchange_class_string) \
                    .has_matrix(self.octobot.evaluator_factory.matrix_id) \
                    .use_tentacles_setup_config(self.octobot.tentacles_setup_config) \
                    .set_bot_id(self.octobot.bot_id) \
                    .is_rest_only()
                if is_trader_enabled_in_config(self.octobot.config):
                    exchange_builder.is_real()
                elif is_trader_simulator_enabled_in_config(self.octobot.config):
                    exchange_builder.is_simulated()
                if backtesting is not None:
                    exchange_builder.is_backtesting(backtesting)
                exchange_manager = await exchange_builder.build()
                await init_exchange_chan_logger(exchange_manager.id)
                self.exchange_manager_ids.append(exchange_manager.id)
            else:
                self.logger.error(f"{exchange_class_string} exchange not found")

    async def _create_backtesting_exchanges(self):
        await initialize_and_run_independent_backtesting(
            create_independent_backtesting(self.octobot.config,
                                           self.octobot.tentacles_setup_config,
                                           get_backtesting_data_files(self.octobot.config)))

    async def create(self) -> bool:
        if is_backtesting_enabled(self.octobot.config):
            await self._create_backtesting_exchanges()
            return False
        if self.octobot.config[CONFIG_EXCHANGES]:
            try:
                await self._create_exchanges()
                return True
            except Exception as e:
                self.logger.exception(e, error_message="An error happened during exchange creation")
        self.logger.error("No exchange in configuration. OctoBot requires at least one exchange "
                          "to read trading data from. You can add exchanges in the configuration section.")
        return False
