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
import copy

from backtesting import backtesting_enabled
from config import CONFIG_DEBUG_OPTION_PERF, TimeFrames, CONFIG_NOTIFICATION_GLOBAL_INFO, \
    NOTIFICATION_STARTING_MESSAGE, CONFIG_NOTIFICATION_INSTANCE
from tentacles_management.advanced_manager import AdvancedManager
from evaluator.evaluator_creator import EvaluatorCreator
from services import ServiceCreator
from tools import get_logger
from tools.notifications import Notification
from tools.performance_analyser import PerformanceAnalyser
from tools.time_frame_manager import TimeFrameManager
from tools.metrics.metrics_manager import MetricsManager


class Initializer:
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.performance_analyser = None
        self.time_frames = None
        self.relevant_evaluators = []

    async def create(self):
        # prepare advanced classes if any
        self._manage_advanced_classes()

        # manage time frames
        self._init_time_frames()

        # initialize evaluators
        self._init_relevant_evaluators()

        # initialize tools
        self._create_performance_analyser()

        # initialize notifications and services
        self._create_notifier()
        await self._create_services()

        self._init_metrics()

    def _manage_advanced_classes(self):
        AdvancedManager.init_advanced_classes_if_necessary(self.octobot.get_config())

    def _init_relevant_evaluators(self):
        # Init relevant evaluator names list using enabled strategies
        self.relevant_evaluators = EvaluatorCreator.get_relevant_evaluators_from_strategies(self.octobot.get_config())

    def _create_performance_analyser(self):
        if CONFIG_DEBUG_OPTION_PERF in self.octobot.get_config() \
                and self.octobot.get_config()[CONFIG_DEBUG_OPTION_PERF]:
            return PerformanceAnalyser()

    def _create_notifier(self):
        self.octobot.get_config()[CONFIG_NOTIFICATION_INSTANCE] = Notification(self.octobot.get_config())

    def _init_time_frames(self):
        # Init time frames using enabled strategies
        EvaluatorCreator.init_time_frames_from_strategies(self.octobot.get_config())
        self.time_frames = copy.copy(TimeFrameManager.get_config_time_frame(self.octobot.get_config()))

        # Init display time frame
        config_time_frames = TimeFrameManager.get_config_time_frame(self.octobot.get_config())
        if TimeFrames.ONE_HOUR not in config_time_frames and not backtesting_enabled(self.octobot.get_config()):
            config_time_frames.append(TimeFrames.ONE_HOUR)
            TimeFrameManager.sort_config_time_frames(self.octobot.get_config())

    async def _create_services(self):
        # Add services to self.octobot.get_config()[CONFIG_CATEGORY_SERVICES]
        await ServiceCreator.create_services(self.octobot.get_config(), backtesting_enabled(self.octobot.get_config()))

        # Notify starting
        if self.octobot.get_config()[CONFIG_NOTIFICATION_INSTANCE].enabled(CONFIG_NOTIFICATION_GLOBAL_INFO):
            await self.octobot.get_config()[CONFIG_NOTIFICATION_INSTANCE].notify_with_all(NOTIFICATION_STARTING_MESSAGE,
                                                                                          False)

    def _init_metrics(self):
        if not backtesting_enabled(self.octobot.get_config()):
            self.octobot.metrics_handler = MetricsManager(self.octobot)
