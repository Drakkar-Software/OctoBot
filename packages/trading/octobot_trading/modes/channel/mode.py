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
import typing

import async_channel.constants as channel_constants
import async_channel.enums as channel_enums
import octobot_commons.signals as commons_signals

import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.constants as constants


class ModeChannelConsumer(exchanges_channel.ExchangeChannelInternalConsumer):
    pass


class ModeChannelProducer(exchanges_channel.ExchangeChannelProducer):
    async def send(self,
                   final_note=constants.ZERO,
                   trading_mode_name=channel_constants.CHANNEL_WILDCARD,
                   state=channel_constants.CHANNEL_WILDCARD,
                   cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                   symbol=channel_constants.CHANNEL_WILDCARD,
                   time_frame=None,
                   data=None,
                   dependencies: typing.Optional[commons_signals.SignalDependencies] = None):
        for consumer in self.channel.get_filtered_consumers(trading_mode_name=trading_mode_name,
                                                            state=state,
                                                            cryptocurrency=cryptocurrency,
                                                            symbol=symbol,
                                                            time_frame=time_frame):
            await consumer.queue.put({
                "final_note": final_note,
                "state": state,
                "trading_mode_name": trading_mode_name,
                "cryptocurrency": cryptocurrency,
                "symbol": symbol,
                "time_frame": time_frame,
                "data": data,
                "dependencies": dependencies
            })


class ModeChannel(exchanges_channel.ExchangeChannel):
    PRODUCER_CLASS = ModeChannelProducer
    CONSUMER_CLASS = ModeChannelConsumer
    DEFAULT_PRIORITY_LEVEL = channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value

    TRADING_MODE_NAME_KEY = "trading_mode_name"
    STATE_KEY = "state"
    CRYPTOCURRENCY_KEY = "cryptocurrency"
    SYMBOL_KEY = "symbol"
    TIME_FRAME_KEY = "time_frame"

    async def new_consumer(self,
                           callback: object = None,  # shouldn't be provided here (InternalConsumer)
                           consumer_instance: ModeChannelConsumer = None,
                           trading_mode_name: str = channel_constants.CHANNEL_WILDCARD,
                           state=channel_constants.CHANNEL_WILDCARD,
                           cryptocurrency: str = channel_constants.CHANNEL_WILDCARD,
                           symbol: str = channel_constants.CHANNEL_WILDCARD,
                           time_frame=None):
        await self._add_new_consumer_and_run(consumer_instance,
                                             trading_mode_name=trading_mode_name,
                                             state=state,
                                             cryptocurrency=cryptocurrency,
                                             symbol=symbol,
                                             time_frame=time_frame)

    def get_filtered_consumers(self,
                               trading_mode_name=channel_constants.CHANNEL_WILDCARD,
                               state=channel_constants.CHANNEL_WILDCARD,
                               cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                               symbol=channel_constants.CHANNEL_WILDCARD,
                               time_frame=channel_constants.CHANNEL_WILDCARD):
        return self.get_consumer_from_filters({
            self.TRADING_MODE_NAME_KEY: trading_mode_name,
            self.STATE_KEY: state,
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol,
            self.TIME_FRAME_KEY: time_frame
        })

    async def _add_new_consumer_and_run(self, consumer,
                                        trading_mode_name=channel_constants.CHANNEL_WILDCARD,
                                        state=channel_constants.CHANNEL_WILDCARD,
                                        cryptocurrency=channel_constants.CHANNEL_WILDCARD,
                                        symbol=channel_constants.CHANNEL_WILDCARD,
                                        time_frame=None):
        consumer_filters: dict = {
            self.TRADING_MODE_NAME_KEY: trading_mode_name,
            self.STATE_KEY: state,
            self.CRYPTOCURRENCY_KEY: cryptocurrency,
            self.SYMBOL_KEY: symbol
        }

        if time_frame:
            consumer_filters[self.TIME_FRAME_KEY] = time_frame

        self.add_new_consumer(consumer, consumer_filters)
        await consumer.run()
        self.logger.debug(f"Consumer started for : "
                          f"[trading_mode_name={trading_mode_name},"
                          f" state={state},"
                          f" cryptocurrency={cryptocurrency},"
                          f" symbol={symbol},"
                          f" time_frame={time_frame}]")
