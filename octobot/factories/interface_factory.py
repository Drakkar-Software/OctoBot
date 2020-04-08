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

from octobot.constants import PROJECT_NAME, LONG_VERSION
from octobot_interfaces.api.interfaces import create_interface_factory, initialize_global_project_data, is_enabled, \
    start_interfaces, is_enabled_in_backtesting
from octobot_interfaces.util.bot import get_bot_api
from octobot_notifications.api.notification import create_notifier_factory, is_enabled_in_config
from octobot.logger import get_logger


class InterfaceFactory:
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
        in_backtesting = False
        try:
            from octobot_backtesting.api.backtesting import is_backtesting_enabled
            in_backtesting = is_backtesting_enabled(self.octobot.config)
        except ImportError:
            # If can't import octobot_backtesting, this session can't be a backtesting one, nothing to do
            pass
        await self._create_interfaces(in_backtesting)
        await self._create_notifiers(in_backtesting)

    async def start_interfaces(self):
        to_start_interfaces = self.interface_list
        started_interfaces = await start_interfaces(to_start_interfaces)
        if len(started_interfaces) != len(to_start_interfaces):
            missing_interfaces = [interface.get_name()
                                  for interface in to_start_interfaces
                                  if interface not in started_interfaces]
            self.logger.error(
                f"{', '.join(missing_interfaces)} interface{'s' if len(missing_interfaces) > 1 else ''} "
                f"did not start properly.")

    async def _create_interfaces(self, in_backtesting):
        # do not overwrite data in case of inner bots init (backtesting)
        if get_bot_api() is None:
            initialize_global_project_data(self.octobot.octobot_api, PROJECT_NAME, LONG_VERSION)
        interface_factory = create_interface_factory(self.octobot.config)
        interface_list = interface_factory.get_available_interfaces()
        for interface_class in interface_list:
            await self._create_interface_if_relevant(interface_factory, interface_class, in_backtesting)

    async def _create_notifiers(self, in_backtesting):
        notifier_factory = create_notifier_factory(self.octobot.config)
        notifier_list = notifier_factory.get_available_notifiers()
        for notifier_class in notifier_list:
            await self._create_notifier_class_if_relevant(notifier_factory, notifier_class, in_backtesting)

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
               (not backtesting_enabled or (backtesting_enabled and is_enabled_in_backtesting(interface_class)))

    def _is_notifier_relevant(self, notifier_class, backtesting_enabled):
        return is_enabled_in_config(notifier_class, self.octobot.config) and \
               notifier_class.REQUIRED_SERVICE.get_is_enabled(self.octobot.config) and \
               not backtesting_enabled
