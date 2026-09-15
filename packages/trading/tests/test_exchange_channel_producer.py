#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest

import octobot_trading.exchange_channel as exchange_channel_module

pytestmark = pytest.mark.asyncio


class TestExchangeChannelProducerPause:
    async def test_does_not_log_when_exchange_only(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binance"
        exchange_manager.should_log_exchange_lifecycle_debug = mock.Mock(return_value=False)
        channel = mock.Mock()
        channel.exchange_manager = exchange_manager
        channel.is_paused = False
        producer = exchange_channel_module.ExchangeChannelProducer(channel)
        producer.logger = mock.Mock()

        await producer.pause()

        producer.logger.debug.assert_not_called()
        assert producer.is_running is False
        assert channel.is_paused is True

    async def test_logs_when_lifecycle_debug_enabled(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binance"
        exchange_manager.should_log_exchange_lifecycle_debug = mock.Mock(return_value=True)
        channel = mock.Mock()
        channel.exchange_manager = exchange_manager
        channel.is_paused = False
        producer = exchange_channel_module.ExchangeChannelProducer(channel)
        producer.logger = mock.Mock()

        await producer.pause()

        producer.logger.debug.assert_called_once_with("Pausing...")


class TestExchangeChannelProducerResume:
    async def test_does_not_log_when_exchange_only(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binance"
        exchange_manager.should_log_exchange_lifecycle_debug = mock.Mock(return_value=False)
        channel = mock.Mock()
        channel.exchange_manager = exchange_manager
        channel.is_paused = True
        producer = exchange_channel_module.ExchangeChannelProducer(channel)
        producer.logger = mock.Mock()

        await producer.resume()

        producer.logger.debug.assert_not_called()
        assert channel.is_paused is False

    async def test_logs_when_lifecycle_debug_enabled(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binance"
        exchange_manager.should_log_exchange_lifecycle_debug = mock.Mock(return_value=True)
        channel = mock.Mock()
        channel.exchange_manager = exchange_manager
        channel.is_paused = True
        producer = exchange_channel_module.ExchangeChannelProducer(channel)
        producer.logger = mock.Mock()

        await producer.resume()

        producer.logger.debug.assert_called_once_with("Resuming...")
