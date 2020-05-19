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
from octobot_trading.api.exchange import get_exchange_configuration_from_exchange_id
from octobot_trading.consumers.octobot_channel_consumer import OctoBotChannelTradingActions as TradingActions, \
    OctoBotChannelTradingDataKeys as TradingKeys, octobot_channel_callback as octobot_channel_trading_callback
from octobot_evaluators.consumers.octobot_channel_consumer import OctoBotChannelEvaluatorActions as EvaluatorActions, \
    octobot_channel_callback as octobot_channel_evaluator_callback
from octobot_services.consumers.octobot_channel_consumer import OctoBotChannelServiceActions as ServiceActions, \
    OctoBotChannelServiceDataKeys as ServiceKeys, octobot_channel_callback as octobot_channel_service_callback


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

        # Initialize evaluator consumer
        self.octobot_channel_consumers.append(
            await self.octobot_channel.new_consumer(
                octobot_channel_evaluator_callback,
                bot_id=self.octobot.bot_id,
                action=[action.value for action in EvaluatorActions]
            ))

        # Initialize service consumer
        self.octobot_channel_consumers.append(
            await self.octobot_channel.new_consumer(
                octobot_channel_service_callback,
                bot_id=self.octobot.bot_id,
                action=[action.value for action in ServiceActions]
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
                    self.octobot.exchange_producer.exchange_manager_ids.append(exchange_id)
                    await init_exchange_chan_logger(exchange_id)
                    exchange_configuration = get_exchange_configuration_from_exchange_id(exchange_id)
                    await self.octobot.evaluator_producer.create_evaluators(exchange_configuration)
                    # If an exchange is created before interface producer is done, it will be registered via
                    # self.octobot.interface_producer directly on creation
                    await self.octobot.interface_producer.register_exchange(exchange_id)
            elif action == EvaluatorActions.EVALUATOR.value:
                if not self.octobot.service_feed_producer.started:
                    # Start service feeds now that evaluators registered their feed requirements
                    await self.octobot.service_feed_producer.start_feeds()
            elif action == ServiceActions.INTERFACE.value:
                await self.octobot.interface_producer.register_interface(data[ServiceKeys.INSTANCE.value])
            elif action == ServiceActions.NOTIFICATION.value:
                await self.octobot.interface_producer.register_notifier(data[ServiceKeys.INSTANCE.value])
            elif action == ServiceActions.SERVICE_FEED.value:
                await self.octobot.service_feed_producer.register_service_feed(data[ServiceKeys.INSTANCE.value])

    async def stop(self) -> None:
        """
        Remove all OctoBot Channel consumers
        """
        for consumer in self.octobot_channel_consumers:
            await self.octobot_channel.remove_consumer(consumer)
