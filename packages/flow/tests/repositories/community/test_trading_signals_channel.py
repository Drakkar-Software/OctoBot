import asyncio
import mock
import pytest
import pytest_asyncio

import async_channel.channels as async_channel_channels

import octobot_copy.entities as copy_entities

import octobot_flow.entities
import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
import octobot_flow.repositories.community.trading_signals_repository as trading_signals_repository


@pytest.fixture
def internal_channel_name():
    return trading_signals_channel.InternalTradingSignalChannel.get_name()


@pytest.fixture(autouse=True)
def reset_internal_trading_signal_channel(internal_channel_name):
    async_channel_channels.del_chan(internal_channel_name)
    yield
    async_channel_channels.del_chan(internal_channel_name)


@pytest_asyncio.fixture(autouse=True)
async def shutdown_internal_trading_signal_channel_after_test(reset_internal_trading_signal_channel):
    """Ensure async channel teardown (stop / flush / del_chan) runs before sync reset del_chan."""
    try:
        yield
    finally:
        await trading_signals_channel.shutdown_internal_trading_signal_channel()


@pytest.mark.asyncio
async def test_insert_trading_signal_delivers_to_subscriber(internal_channel_name):
    received: list[octobot_flow.entities.TradingSignal] = []

    async def capture_callback(trading_signal: octobot_flow.entities.TradingSignal) -> None:
        received.append(trading_signal)

    channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    await channel.new_consumer(capture_callback)

    account = copy_entities.Account()
    signal = octobot_flow.entities.TradingSignal(account=account, strategy_id="test-strategy-id")
    repository = trading_signals_repository.TradingSignalsRepository(mock.MagicMock())
    with mock.patch.object(
        repository,
        "_upload_trading_signal",
        mock.AsyncMock(),
    ) as mock_upload_signal:
        await repository.insert_trading_signal(signal)

    mock_upload_signal.assert_called_once_with(signal)

    await asyncio.sleep(0.05)
    assert len(received) == 1
    assert received[0] is signal


@pytest.mark.asyncio
async def test_get_or_create_internal_trading_signal_channel_is_idempotent(internal_channel_name):
    first = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    second = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    assert first is second


@pytest.mark.asyncio
async def test_shutdown_internal_trading_signal_channel_allows_recreate(internal_channel_name):
    await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    await trading_signals_channel.shutdown_internal_trading_signal_channel()
    with pytest.raises(KeyError):
        async_channel_channels.get_chan(internal_channel_name)

    new_channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    assert new_channel is not None
