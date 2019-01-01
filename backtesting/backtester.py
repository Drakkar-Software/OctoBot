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

from trading.exchanges.exchange_simulator.exchange_simulator import ExchangeSimulator
from backtesting.backtesting_util import start_backtesting_bot, get_standalone_backtesting_bot


class Backtester:

    def __init__(self, config, files=None):
        if files is None:
            files = []
        self.octobot, self.ignored_files = get_standalone_backtesting_bot(config, files)
        self.error = None

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
        return await start_backtesting_bot(self.octobot, in_thread=in_thread, watcher=self)

    def get_bot(self):
        return self.octobot

    def set_error(self, error):
        self.error = error
