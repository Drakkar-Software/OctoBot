import asyncio

import pytest

import async_channel.channels as async_channel_channels

pytest.importorskip("octobot_flow")

import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
import octobot_flow.repositories.community.trading_signals_repository as trading_signals_repository
import octobot_node.scheduler.internal_trading_signals as internal_trading_signals


def _channel_name() -> str:
    return trading_signals_channel.InternalTradingSignalChannel.get_name()


@pytest.mark.asyncio
async def test_subscribe_internal_trading_signal_consumer_registers_consumer():
    async_channel_channels.del_chan(_channel_name())
    await internal_trading_signals.subscribe_internal_trading_signal_consumer()
    channel = async_channel_channels.get_chan(_channel_name())
    assert len(channel.get_consumers()) >= 1
    await trading_signals_channel.shutdown_internal_trading_signal_channel()


@pytest.mark.asyncio
async def test_shutdown_internal_trading_signal_channel_after_subscribe_unregisters():
    async_channel_channels.del_chan(_channel_name())
    await internal_trading_signals.subscribe_internal_trading_signal_consumer()
    await trading_signals_channel.shutdown_internal_trading_signal_channel()
    with pytest.raises(KeyError):
        async_channel_channels.get_chan(_channel_name())


@pytest.mark.asyncio
async def test_get_or_create_after_shutdown_creates_new_channel():
    async_channel_channels.del_chan(_channel_name())
    await internal_trading_signals.subscribe_internal_trading_signal_consumer()
    await trading_signals_channel.shutdown_internal_trading_signal_channel()
    new_channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    assert new_channel is not None
    await trading_signals_channel.shutdown_internal_trading_signal_channel()


@pytest.mark.asyncio
async def test_insert_trading_signal_completes_without_error_after_subscribe():
    import octobot_copy.entities as copy_entities
    import octobot_flow.entities as flow_entities

    async_channel_channels.del_chan(_channel_name())
    await internal_trading_signals.subscribe_internal_trading_signal_consumer()
    signal = flow_entities.TradingSignal(account=copy_entities.Account(), strategy_id="test-strategy-id")
    repository = trading_signals_repository.TradingSignalsRepository(object())  # type: ignore[arg-type]
    await repository.insert_trading_signal(signal)
    await asyncio.sleep(0.05)
    await trading_signals_channel.shutdown_internal_trading_signal_channel()
