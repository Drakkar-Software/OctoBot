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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
from octobot.channels.octobot_channel import OctoBotChannel
from octobot.logger import init_exchange_chan_logger
from octobot_channels.channels.channel_instances import set_chan_at_id
from octobot_channels.util.channel_creator import create_channel_instance
from octobot_commons.enums import OctoBotChannelSubjects
from octobot_commons.logging.logging_util import get_logger
from octobot_trading.consumers.octobot_channel_consumer import OctoBotChannelTradingActions as TradingActions, \
    OctoBotChannelTradingDataKeys as TradingKeys, octobot_channel_callback as octobot_channel_trading_callback


class OctoBotChannelGlobalConsumer:

    def __init__(self, octobot):
        self.octobot = octobot
        self.logger = get_logger(self.__class__.__name__)

        # the list of octobot channel consumers
        self.octobot_channel_consumers = []

        # the OctoBot Channel instance
        self.octobot_channel = None

    async def initialize(self):
        # Creates OctoBot Channel
        self.octobot_channel = await create_channel_instance(OctoBotChannel, set_chan_at_id, is_synchronized=True,
                                                             bot_id=self.octobot.bot_id)

        # Initialize global consumer
        self.octobot_channel_consumers.append(
            await self.octobot_channel.new_consumer(self.octobot_channel_callback, bot_id=self.octobot.bot_id))

        # Initialize trading consumer
        self.octobot_channel_consumers.append(
            await self.octobot_channel.new_consumer(
                octobot_channel_trading_callback,
                bot_id=self.octobot.bot_id,
                action=[action.value for action in TradingActions]
            ))

    async def octobot_channel_callback(self, bot_id, subject, action, data) -> None:
        """
        OctoBot channel consumer callback
        :param bot_id: the callback bot id
        :param subject: the callback subject
        :param action: the callback action
        :param data: the callback data
        """
        if subject == OctoBotChannelSubjects.NOTIFICATION.value:
            if action == TradingActions.EXCHANGE.value:
                if TradingKeys.EXCHANGE_ID.value in data:
                    exchange_id = data[TradingKeys.EXCHANGE_ID.value]
                    await init_exchange_chan_logger(exchange_id)

    async def stop(self) -> None:
        """
        Remove all OctoBot Channel consumers
        """
        for consumer in self.octobot_channel_consumers:
            await self.octobot_channel.remove_consumer(consumer)
