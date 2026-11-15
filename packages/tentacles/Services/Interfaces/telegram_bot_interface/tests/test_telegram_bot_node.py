#  Drakkar-Software OctoBot-Tentacles

import mock
import pytest

import octobot_services.interfaces.bots.node_command_format as node_command_format
import tentacles.Services.Interfaces.telegram_bot_interface.telegram_bot as telegram_bot_module


@pytest.mark.asyncio
class TestTelegramBotNodeHandlers:
    async def test_fees_sends_one_message_per_automation(self):
        update = mock.Mock()
        update.effective_message = mock.AsyncMock()
        with (
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_is_valid_user", return_value=True),
            mock.patch.object(
                telegram_bot_module.interfaces_bots.AbstractBotInterface,
                "get_command_fees",
                mock.AsyncMock(return_value=["Alpha fees", "Beta fees"]),
            ),
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_send_message", mock.AsyncMock()) as send_mock,
        ):
            await telegram_bot_module.TelegramBotInterface.command_fees(update, None)
        assert send_mock.await_count == 2
        assert send_mock.await_args_list[0].args[1] == "Alpha fees"
        assert send_mock.await_args_list[1].args[1] == "Beta fees"

    async def test_fees_empty_automations_sends_no_bots_message(self):
        update = mock.Mock()
        update.effective_message = mock.AsyncMock()
        with (
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_is_valid_user", return_value=True),
            mock.patch.object(
                telegram_bot_module.interfaces_bots.AbstractBotInterface,
                "get_command_fees",
                mock.AsyncMock(return_value=[node_command_format.NODE_NO_AUTOMATIONS_MESSAGE]),
            ),
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_send_message", mock.AsyncMock()) as send_mock,
        ):
            await telegram_bot_module.TelegramBotInterface.command_fees(update, None)
        assert node_command_format.NODE_NO_AUTOMATIONS_MESSAGE in send_mock.await_args.args[1]

    async def test_sell_all_refused_on_node(self):
        update = mock.Mock()
        update.effective_message = mock.AsyncMock()
        with (
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_is_valid_user", return_value=True),
            mock.patch.object(
                telegram_bot_module.interfaces_bots.AbstractBotInterface,
                "get_command_sell_all",
                mock.AsyncMock(return_value=node_command_format.NODE_COMMAND_UNAVAILABLE_MESSAGE),
            ),
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_send_message", mock.AsyncMock()) as send_mock,
        ):
            await telegram_bot_module.TelegramBotInterface.command_sell_all(
                update, mock.Mock(args=["BTC"])
            )
        assert node_command_format.NODE_COMMAND_UNAVAILABLE_MESSAGE in send_mock.await_args.args[1]

    async def test_profitability_refused_on_node(self):
        update = mock.Mock()
        update.effective_message = mock.AsyncMock()
        with (
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_is_valid_user", return_value=True),
            mock.patch.object(
                telegram_bot_module.interfaces_bots.AbstractBotInterface,
                "get_command_profitability",
                return_value=node_command_format.NODE_COMMAND_UNAVAILABLE_MESSAGE,
            ),
            mock.patch.object(telegram_bot_module.TelegramBotInterface, "_send_message", mock.AsyncMock()) as send_mock,
        ):
            await telegram_bot_module.TelegramBotInterface.command_profitability(update, None)
        assert send_mock.await_args.args[1] == node_command_format.NODE_COMMAND_UNAVAILABLE_MESSAGE