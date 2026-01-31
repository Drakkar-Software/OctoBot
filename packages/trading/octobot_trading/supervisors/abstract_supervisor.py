#  Drakkar-Software OctoBot-Trading
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
import abc

import octobot_commons.logging as logging
import octobot_commons.tentacles_management as abstract_tentacle
import octobot_tentacles_manager.api as tentacles_manager_api


class AbstractSupervisor(abstract_tentacle.AbstractTentacle):
    __metaclass__ = abc.ABCMeta

    def __init__(self, config, exchange_manager):
        super().__init__()
        self.logger = logging.get_logger(self.get_name())

        # Global OctoBot configuration
        self.config: dict = config

        # Mode related exchange manager instance
        self.exchange_manager = exchange_manager

        # The id of the OctoBot using this trading mode
        self.bot_id: str = None

        # Supervisor specific config (Is loaded from tentacle specific file)
        self.supervisor_config: dict = None

        # If this supervisor is enabled
        self.enabled: bool = True

        # producers is the list of producers created by this supervisor instance
        self.producers = []

        # producers is the list of consumers created by this supervisor instance
        self.consumers = []

    @classmethod
    def get_parent_supervisor_classes(cls, higher_parent_class_limit=None) -> list:
        return [
            class_type
            for class_type in cls.mro()
            if (higher_parent_class_limit if higher_parent_class_limit else AbstractSupervisor) in class_type.mro()
        ]

    @staticmethod
    def is_backtestable() -> bool:
        """
        Should be overwritten
        :return: True if the Supervisor can be used in a backtesting else False
        """
        return True

    async def initialize(self) -> None:
        """
        Initialize supervisor
        """

    async def stop(self) -> None:
        """
        Stops all producers and consumers and clean references
        """
        for producer in self.producers:
            await producer.stop()
        for consumer in self.consumers:
            await consumer.stop()
        self.exchange_manager = None

    def load_config(self) -> None:
        """
        Try to load Supervisor tentacle config.
        Calls set_default_config() if the tentacle config is empty
        """
        # try with this class name
        self.supervisor_config = tentacles_manager_api.get_tentacle_config(self.exchange_manager.tentacles_setup_config,
                                                                           self.__class__)

        # set default config if nothing found
        if not self.supervisor_config:
            self.set_default_config()

    # to implement in subclasses if config is necessary
    def set_default_config(self) -> None:
        pass
