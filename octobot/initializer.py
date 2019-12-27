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
from config import PROJECT_NAME, LONG_VERSION
from octobot_backtesting.api.backtesting import is_backtesting_enabled
from octobot_interfaces.api.interfaces import create_interface_factory, initialize_global_project_data, is_enabled
from octobot_interfaces.util.bot import get_bot
from octobot_notifications.api.notification import create_notifier_factory, is_enabled_in_config
from tools import get_logger


class Initializer:
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.interface_list = []
        self.notifier_list = []

    async def create(self):
        # initialize tools
        self.__init_metrics()
        await self._create_interfaces()
        await self._create_notifiers()

    async def _create_interfaces(self):
        # do not overwrite data in case of inner bots init (backtesting)
        if get_bot() is None:
            initialize_global_project_data(self.octobot, PROJECT_NAME, LONG_VERSION)
        interface_factory = create_interface_factory(self.octobot.config)
        interface_list = interface_factory.get_available_interfaces()
        backtesting_enabled = is_backtesting_enabled(self.octobot.config)
        for interface_class in interface_list:
            await self._create_interface_if_relevant(interface_factory, interface_class, backtesting_enabled)

    async def _create_notifiers(self):
        notifier_factory = create_notifier_factory(self.octobot.config)
        notifier_list = notifier_factory.get_available_notifiers()
        backtesting_enabled = is_backtesting_enabled(self.octobot.config)
        for notifier_class in notifier_list:
            await self._create_notifier_class_if_relevant(notifier_factory, notifier_class, backtesting_enabled)

    async def _create_interface_if_relevant(self, interface_factory, interface_class, backtesting_enabled):
        if self._is_interface_relevant(interface_class, backtesting_enabled):
            interface_instance = await interface_factory.create_interface(interface_class)
            await interface_instance.initialize(backtesting_enabled)
            self.interface_list.append(interface_instance)

    async def _create_notifier_class_if_relevant(self, notifier_factory, notifier_class, backtesting_enabled):
        if self._is_notifier_relevant(notifier_class, backtesting_enabled):
            notifier_instance = await notifier_factory.create_notifier(notifier_class)
            await notifier_instance.initialize(backtesting_enabled)
            self.notifier_list.append(notifier_instance)

    def _is_interface_relevant(self, interface_class, backtesting_enabled):
        return is_enabled(interface_class) and \
               interface_class.REQUIRED_SERVICE.get_is_enabled(self.octobot.config) and \
               (not backtesting_enabled or interface_class.REQUIRED_SERVICE.BACKTESTING_ENABLED)

    def _is_notifier_relevant(self, notifier_class, backtesting_enabled):
        return is_enabled_in_config(notifier_class, self.octobot.config) and \
               notifier_class.REQUIRED_SERVICE.get_is_enabled(self.octobot.config) and \
               not backtesting_enabled

    def __init_metrics(self):
        pass  # TODO
