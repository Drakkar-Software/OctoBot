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

from copy import copy

from tools.logging.logging_util import BotLogger
from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from backtesting.backtesting_util import start_backtesting_bot, get_standalone_backtesting_bot
from tools.config_manager import ConfigManager


class Backtester:

    def __init__(self, config, source, files=None, reset_tentacle_config=False):
        if files is None:
            files = []
        backtester_config = config
        if reset_tentacle_config:
            backtester_config = ConfigManager.reload_tentacle_config(copy(config))
        self.octobot, self.ignored_files = get_standalone_backtesting_bot(backtester_config, files)
        self.error = None
        self._source = source
        self.finished_source = None
        self.errors_count = None

    def get_finished_source(self):
        return self.finished_source

    def get_ignored_files(self):
        return self.ignored_files

    def get_is_computing(self):
        if self.error is not None:
            return False
        simulator = self._get_exchange_simulator()
        if simulator:
            return simulator.get_is_initializing() or not simulator.get_backtesting().get_is_finished()
        return False

    def get_progress(self):
        simulator = self._get_exchange_simulator()
        if simulator:
            return simulator.get_progress()
        return 0

    async def get_report(self):
        simulator = self._get_exchange_simulator()
        if simulator:
            report = await simulator.get_backtesting().get_dict_formatted_report()
            if self.errors_count is None:
                self.errors_count = BotLogger.get_backtesting_errors()
            report["errors_count"] = self.errors_count
            if self.error is not None:
                report["error"] = str(self.error)
            return report
        return {}

    def _get_exchange_simulator(self):
        for exchange in self.octobot.get_exchanges_list().values():
            if isinstance(exchange.get_exchange(), ExchangeSimulator):
                return exchange.get_exchange()

    async def start_backtesting(self, in_thread=False):
        self.error = None
        try:
            result = await start_backtesting_bot(self.octobot, in_thread=in_thread, watcher=self)
            self.finished_source = self._source
            return result
        except Exception as e:
            self.error = e
            self.finished_source = self._source
            raise e

    def get_bot(self):
        return self.octobot

    def set_error(self, error):
        self.error = error
