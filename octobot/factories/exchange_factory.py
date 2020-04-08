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

from octobot_backtesting.api.backtesting import is_backtesting_enabled, get_backtesting_data_files
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

    async def create(self):
        if self.octobot.config[CONFIG_EXCHANGES]:
            for exchange_class_string in self.octobot.config[CONFIG_EXCHANGES]:
                if exchange_class_string in self.available_exchanges:
                    exchange_builder = create_exchange_builder(self.octobot.config, exchange_class_string) \
                        .has_matrix(self.octobot.evaluator_factory.matrix_id) \
                        .use_tentacles_setup_config(self.octobot.tentacles_setup_config) \
                        .is_rest_only()
                    if is_trader_enabled_in_config(self.octobot.config):
                        exchange_builder.is_real()
                    elif is_trader_simulator_enabled_in_config(self.octobot.config):
                        exchange_builder.is_simulated()
                    if is_backtesting_enabled(self.octobot.config):
                        exchange_builder.is_backtesting(get_backtesting_data_files(self.octobot.config))
                    exchange_manager = await exchange_builder.build()
                    await init_exchange_chan_logger(exchange_manager.id)
                    self.exchange_manager_ids.append(exchange_manager.id)
                else:
                    self.logger.error(f"{exchange_class_string} exchange not found")
        else:
            self.logger.error("No exchange in configuration. OctoBot requires at least one exchange "
                              "to read trading data from. You can add exchanges in the configuration section.")
