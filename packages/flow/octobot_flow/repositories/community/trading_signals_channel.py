import typing

import async_channel.channels as async_channel_channels
import async_channel.consumer as async_channel_consumer
import async_channel.enums as async_channel_enums
import async_channel.producer as async_channel_producer
import async_channel.util.channel_creator as async_channel_channel_creator

import octobot_flow.entities

INTERNAL_TRADING_SIGNAL_KEY = "trading_signal"


class InternalTradingSignalChannelConsumer(async_channel_consumer.Consumer):
    pass


class InternalTradingSignalChannelProducer(async_channel_producer.Producer):
    pass


class InternalTradingSignalChannel(async_channel_channels.Channel):
    PRODUCER_CLASS = InternalTradingSignalChannelProducer
    CONSUMER_CLASS = InternalTradingSignalChannelConsumer
    DEFAULT_PRIORITY_LEVEL = async_channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value


async def get_or_create_internal_trading_signal_channel() -> InternalTradingSignalChannel:
    channel_name = InternalTradingSignalChannel.get_name()
    try:
        return typing.cast(
            InternalTradingSignalChannel,
            async_channel_channels.get_chan(channel_name),
        )
    except KeyError:
        created = await async_channel_channel_creator.create_channel_instance(
            InternalTradingSignalChannel,
            async_channel_channels.set_chan,
        )
        return typing.cast(InternalTradingSignalChannel, created)


async def send_internal_trading_signal(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    channel = await get_or_create_internal_trading_signal_channel()
    internal_producer = channel.get_internal_producer()
    await internal_producer.send({INTERNAL_TRADING_SIGNAL_KEY: trading_signal})


async def shutdown_internal_trading_signal_channel() -> None:
    channel_name = InternalTradingSignalChannel.get_name()
    try:
        channel = async_channel_channels.get_chan(channel_name)
    except KeyError:
        return
    await channel.stop()
    channel.flush()
    async_channel_channels.del_chan(channel_name)
