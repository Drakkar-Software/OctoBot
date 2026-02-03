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
import octobot_commons.channels_name as channels_names
import async_channel.util as channel_creator
import async_channel.channels as channels
import octobot_trading.signals.channel.remote_trading_signal as remote_trading_signal
import octobot_trading.signals.channel.signal_producer as signal_producer


async def create_remote_trading_signal_channel_if_missing(exchange_manager) -> \
        (remote_trading_signal.RemoteTradingSignalsChannel, bool):
    try:
        return channels.get_chan(channels_names.OctoBotCommunityChannelsName.REMOTE_TRADING_SIGNALS_CHANNEL.value), \
               False
    except KeyError:
        channel = await channel_creator.create_channel_instance(remote_trading_signal.RemoteTradingSignalsChannel,
                                                                channels.set_chan)
        # also create the associated producer
        producer = signal_producer.RemoteTradingSignalProducer(
            channel,
            exchange_manager.bot_id
        )
        await channel.register_producer(producer)
        return channel, True
