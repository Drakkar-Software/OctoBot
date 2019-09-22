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

from config import CONFIG_DEBUG_OPTION_PERF
from tools import get_logger
from tools.metrics.metrics_manager import MetricsManager
from tools.performance_analyser import PerformanceAnalyser


class Initializer:
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.performance_analyser = None

    async def create(self):
        # initialize tools
        self.performance_analyser = self.__create_performance_analyser()

        self.__init_metrics()

    def __create_performance_analyser(self):
        if CONFIG_DEBUG_OPTION_PERF in self.octobot.config and self.octobot.config[CONFIG_DEBUG_OPTION_PERF]:
            return PerformanceAnalyser()

    def __init_metrics(self):
        # if not backtesting_enabled(self.octobot.config):
        #     self.octobot.metrics_handler = MetricsManager(self.octobot)
        pass  # TODO
