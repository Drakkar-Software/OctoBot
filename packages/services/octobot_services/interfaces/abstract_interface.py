#  Drakkar-Software OctoBot-Services
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

import octobot_commons.channels_name as channels_names
import async_channel.util as channel_creator
import async_channel.channels as channels
import octobot_services.channel as service_channels
import octobot_services.abstract_service_user as abstract_service_user
import octobot_services.util as util


class AbstractInterface(abstract_service_user.AbstractServiceUser, util.ReturningStartable, util.ExchangeWatcher):
    __metaclass__ = abc.ABCMeta
    # The service required to run this interface
    REQUIRED_SERVICES = None

    # References that will be shared by interfaces
    bot_api = None
    project_name = None
    project_version = None
    enabled = True

    def __init__(self, config):
        abstract_service_user.AbstractServiceUser.__init__(self, config)
        util.ExchangeWatcher.__init__(self)

    async def _initialize_impl(self, backtesting_enabled, edited_config) -> bool:
        if await abstract_service_user.AbstractServiceUser._initialize_impl(self, backtesting_enabled, edited_config):
            await self._create_user_commands_channel_if_not_existing()
            return True
        return False

    @staticmethod
    def initialize_global_project_data(bot_api, project_name, project_version):
        AbstractInterface.bot_api = bot_api
        AbstractInterface.project_name = project_name
        AbstractInterface.project_version = project_version

    @staticmethod
    def get_exchange_managers():
        try:
            import octobot_trading.api as api
            return api.get_exchange_managers_from_exchange_ids(AbstractInterface.bot_api.get_exchange_manager_ids())
        except ImportError:
            AbstractInterface.get_logger().error("AbstractInterface requires OctoBot-Trading package installed")

    @staticmethod
    def is_bot_ready():
        return AbstractInterface.bot_api.is_initialized()

    @abc.abstractmethod
    async def stop(self):
        raise NotImplementedError(f"stop is not implemented for {self.get_name()}")

    @staticmethod
    async def _create_user_commands_channel_if_not_existing() -> None:
        try:
            channels.get_chan(channels_names.OctoBotUserChannelsName.USER_COMMANDS_CHANNEL.value)
        except KeyError:
            await channel_creator.create_channel_instance(service_channels.UserCommandsChannel, channels.set_chan)
