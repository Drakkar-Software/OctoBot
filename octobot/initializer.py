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
from octobot_backtesting.api.backtesting import is_backtesting_enabled
from octobot_services.api.services import create_service_factory
from tools import get_logger


class Initializer:
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

    async def create(self):
        # initialize tools
        self.__init_metrics()
        await self._create_services()

    async def _create_services(self):
        service_factory = create_service_factory(self.octobot.config)
        service_list = service_factory.get_available_services()
        backtesting_enabled = is_backtesting_enabled(self.octobot.config)
        for service_class in service_list:
            await self._create_service_if_relevant(service_factory, service_class, backtesting_enabled)

    async def _create_service_if_relevant(self, service_factory, service_class, backtesting_enabled):
        service_instance = service_class()
        if self._is_service_relevant(service_instance, backtesting_enabled):
            service_instance.is_backtesting_enabled = backtesting_enabled
            await service_factory.create_service(service_instance)

    def _is_service_relevant(self, service, backtesting_enabled):
        return service.get_is_enabled(self.octobot.config) and \
                (not backtesting_enabled or service.BACKTESTING_ENABLED)

    def __init_metrics(self):
        pass  # TODO
