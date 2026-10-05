#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_trading.personal_data as trading_personal_data

import octobot_flow.repositories.exchange.channel_producer_ensure as channel_producer_ensure_module

pytestmark = pytest.mark.asyncio


class TestEnsureTemporaryChannelProducer:
    async def test_creates_channels_and_producer_when_no_channels(self):
        exchange_manager = mock.Mock()
        with (
            mock.patch.object(
                channel_producer_ensure_module,
                "exchange_has_registered_channels",
                return_value=False,
            ),
            mock.patch.object(
                channel_producer_ensure_module,
                "channel_has_producer",
                return_value=False,
            ),
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(),
            ) as create_exchange_channels_mock,
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ) as create_producers_mock,
        ):
            await channel_producer_ensure_module.ensure_temporary_channel_producer(
                exchange_manager,
                "Trades",
                trading_personal_data.TradesUpdater,
            )

        create_exchange_channels_mock.assert_awaited_once_with(exchange_manager)
        create_producers_mock.assert_awaited_once_with(
            exchange_manager,
            [trading_personal_data.TradesUpdater],
            start_producers=False,
        )

    async def test_no_op_when_producer_already_registered(self):
        exchange_manager = mock.Mock()
        with (
            mock.patch.object(
                channel_producer_ensure_module,
                "exchange_has_registered_channels",
                return_value=True,
            ),
            mock.patch.object(
                channel_producer_ensure_module,
                "channel_has_producer",
                return_value=True,
            ),
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(),
            ) as create_exchange_channels_mock,
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ) as create_producers_mock,
        ):
            await channel_producer_ensure_module.ensure_temporary_channel_producer(
                exchange_manager,
                "Trades",
                trading_personal_data.TradesUpdater,
            )

        create_exchange_channels_mock.assert_not_called()
        create_producers_mock.assert_not_called()

    async def test_registers_producer_only_when_channels_exist(self):
        exchange_manager = mock.Mock()
        with (
            mock.patch.object(
                channel_producer_ensure_module,
                "exchange_has_registered_channels",
                return_value=True,
            ),
            mock.patch.object(
                channel_producer_ensure_module,
                "channel_has_producer",
                return_value=False,
            ),
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(),
            ) as create_exchange_channels_mock,
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ) as create_producers_mock,
        ):
            await channel_producer_ensure_module.ensure_temporary_channel_producer(
                exchange_manager,
                "Trades",
                trading_personal_data.TradesUpdater,
            )

        create_exchange_channels_mock.assert_not_called()
        create_producers_mock.assert_awaited_once_with(
            exchange_manager,
            [trading_personal_data.TradesUpdater],
            start_producers=False,
        )

    async def test_create_all_channels_if_missing_false_only_adds_producer_when_channels_exist(self):
        exchange_manager = mock.Mock()
        with (
            mock.patch.object(
                channel_producer_ensure_module,
                "exchange_has_registered_channels",
                return_value=True,
            ),
            mock.patch.object(
                channel_producer_ensure_module,
                "channel_has_producer",
                return_value=False,
            ),
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(),
            ) as create_exchange_channels_mock,
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ) as create_producers_mock,
        ):
            await channel_producer_ensure_module.ensure_temporary_channel_producer(
                exchange_manager,
                "Orders",
                trading_personal_data.OrdersUpdater,
                create_all_channels_if_missing=False,
            )

        create_exchange_channels_mock.assert_not_called()
        create_producers_mock.assert_awaited_once_with(
            exchange_manager,
            [trading_personal_data.OrdersUpdater],
            start_producers=False,
        )


class TestChannelHasProducer:
    async def test_returns_false_when_channel_missing(self):
        exchange_manager = mock.Mock()
        exchange_manager.id = "missing-channel-exchange"
        with mock.patch.object(
            channel_producer_ensure_module.exchange_channel_module,
            "get_chan",
            side_effect=KeyError("Channel Balance not found"),
        ):
            has_producer = channel_producer_ensure_module.channel_has_producer(
                exchange_manager,
                "Balance",
            )

        assert has_producer is False
