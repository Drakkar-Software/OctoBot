# pylint: disable=W0237
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
import async_channel.constants as channel_constants
import async_channel.enums as channel_enums
import async_channel.channels as channels
import async_channel.consumer as consumers
import async_channel.producer as producers

import octobot_trading.enums as enums


class RemoteTradingSignalChannelConsumer(consumers.Consumer):
    pass


class RemoteTradingSignalChannelInternalConsumer(consumers.InternalConsumer):
    pass


class RemoteTradingSignalChannelProducer(producers.Producer):
    async def send(self, signal, bot_id, identifier, version):
        for consumer in self.channel.get_filtered_consumers(
                identifier=identifier,
                exchange=signal.content[enums.TradingSignalOrdersAttrs.EXCHANGE.value],
                symbol=signal.content[enums.TradingSignalOrdersAttrs.SYMBOL.value],
                version=version,
                bot_id=bot_id
        ):
            await consumer.queue.put({
                enums.TradingSignalAttrs.IDENTIFIER.value: identifier,
                enums.TradingSignalAttrs.EXCHANGE.value: signal.content[enums.TradingSignalOrdersAttrs.EXCHANGE.value],
                enums.TradingSignalAttrs.SYMBOL.value: signal.content[enums.TradingSignalOrdersAttrs.SYMBOL.value],
                RemoteTradingSignalsChannel.VERSION_KEY: version,
                RemoteTradingSignalsChannel.BOT_ID_KEY: bot_id,
                RemoteTradingSignalsChannel.SIGNAL_KEY: signal,
            })


class RemoteTradingSignalsChannel(channels.Channel):
    PRODUCER_CLASS = RemoteTradingSignalChannelProducer
    CONSUMER_CLASS = RemoteTradingSignalChannelConsumer
    DEFAULT_PRIORITY_LEVEL = channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
    SIGNAL_KEY = "signal"
    BOT_ID_KEY = "bot_id"
    VERSION_KEY = "version"

    async def new_consumer(self,
                           callback: object = None,
                           consumer_instance: object = None,
                           size: int = 0,
                           priority_level: int = DEFAULT_PRIORITY_LEVEL,
                           identifier: str = channel_constants.CHANNEL_WILDCARD,
                           exchange=channel_constants.CHANNEL_WILDCARD,
                           symbol: str = channel_constants.CHANNEL_WILDCARD,
                           version: str = channel_constants.CHANNEL_WILDCARD,
                           bot_id: str = channel_constants.CHANNEL_WILDCARD):
        consumer = consumer_instance if consumer_instance else self.CONSUMER_CLASS(callback,
                                                                                   size=size,
                                                                                   priority_level=priority_level)
        await self._add_new_consumer_and_run(consumer,
                                             identifier=identifier,
                                             exchange=exchange,
                                             symbol=symbol,
                                             version=version,
                                             bot_id=bot_id)
        return consumer

    def get_filtered_consumers(self,
                               identifier=channel_constants.CHANNEL_WILDCARD,
                               exchange=channel_constants.CHANNEL_WILDCARD,
                               symbol=channel_constants.CHANNEL_WILDCARD,
                               version=channel_constants.CHANNEL_WILDCARD,
                               bot_id=channel_constants.CHANNEL_WILDCARD):
        return self.get_consumer_from_filters({
            enums.TradingSignalAttrs.IDENTIFIER.value: identifier,
            enums.TradingSignalAttrs.EXCHANGE.value: exchange,
            enums.TradingSignalAttrs.SYMBOL.value: symbol,
            RemoteTradingSignalsChannel.VERSION_KEY: version,
            RemoteTradingSignalsChannel.BOT_ID_KEY: bot_id,
        })

    async def _add_new_consumer_and_run(self, consumer,
                                        identifier=channel_constants.CHANNEL_WILDCARD,
                                        exchange=channel_constants.CHANNEL_WILDCARD,
                                        symbol=channel_constants.CHANNEL_WILDCARD,
                                        version=channel_constants.CHANNEL_WILDCARD,
                                        bot_id=channel_constants.CHANNEL_WILDCARD):
        consumer_filters: dict = {
            enums.TradingSignalAttrs.IDENTIFIER.value: identifier,
            enums.TradingSignalAttrs.EXCHANGE.value: exchange,
            enums.TradingSignalAttrs.SYMBOL.value: symbol,
            RemoteTradingSignalsChannel.VERSION_KEY: version,
            RemoteTradingSignalsChannel.BOT_ID_KEY: bot_id,
        }

        self.add_new_consumer(consumer, consumer_filters)
        await consumer.run()
        self.logger.debug(f"Consumer started for : "
                          f"[identifier={identifier},"
                          f" exchange={exchange},"
                          f" symbol={symbol},"
                          f" version={version}]"
                          f" bot_id={bot_id}]")

    async def subscribe_to_product_feed(self, feed_id):
        await self.producers[0].subscribe_to_product_feed(feed_id)

    async def stop(self) -> None:
        """
        Stops non-triggered tasks management
        """
        self.logger.debug("Stopping channel: this should normally not be happening unless OctoBot is stopping")
        await super().stop()
