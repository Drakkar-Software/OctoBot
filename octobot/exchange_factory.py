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
import os

import ccxt

from octobot_commons.logging.logging_util import get_logger
from octobot_trading.api.exchange import create_new_exchange
from octobot_trading.constants import CONFIG_EXCHANGES
from tools.logger import init_exchange_chan_logger


class ExchangeFactory:
    """ExchangeFactory class:
    - Create exchanges and trades according to configureated exchanges
    """

    def __init__(self, octobot, ignore_config=False):
        self.octobot = octobot
        self.ignore_config = ignore_config

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.exchange_manager = None
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
                    exchange_factory = create_new_exchange(self.octobot.config, exchange_class_string,
                                                           is_simulated=True,
                                                           is_rest_only=True,
                                                           is_backtesting=False,
                                                           is_sandboxed=False,
                                                           backtesting_files=[os.getenv('BACKTESTING_FILE')])
                    await exchange_factory.create()
                    await init_exchange_chan_logger(exchange_factory.exchange_name)
                else:
                    self.logger.error(f"{exchange_class_string} exchange not found")
        else:
            self.logger.error("No exchange in configuration. OctoBot requires at least one exchange "
                              "to read trading data from. You can add exchanges in the configuration section.")
