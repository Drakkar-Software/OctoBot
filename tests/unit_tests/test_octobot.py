#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import pytest
from mock import Mock, AsyncMock

import octobot_commons.enums as commons_enums

from octobot.automation.bases.execution_details import ExecutionDetails
from octobot.octobot import OctoBot
from octobot_commons.tests.test_config import load_test_config


pytestmark = pytest.mark.asyncio


@pytest.fixture
def octobot_with_mocks():
    """OctoBot with mocked exchange_producer and community_auth for stop_all_trading_modes_and_pause_traders tests."""
    config = load_test_config(dict_only=False)
    mock_community_auth = Mock()
    mock_community_bot = Mock()
    mock_community_bot.schedule_bot_stop = AsyncMock()
    mock_community_bot.insert_stopped_strategy_execution_log = AsyncMock()
    mock_community_auth.community_bot = mock_community_bot

    mock_exchange_producer = Mock()
    mock_exchange_producer.stop_all_trading_modes_and_pause_trader = AsyncMock()

    octobot = OctoBot(config, community_authenticator=mock_community_auth, ignore_config=True)
    octobot.exchange_producer = mock_exchange_producer

    return {
        "octobot": octobot,
        "community_bot": mock_community_bot,
        "exchange_producer": mock_exchange_producer,
    }


class TestOctoBotStopAllTradingModesAndPauseTraders:
    async def test_stop_all_trading_modes_and_pause_traders_calls_exchange_producer_and_community_bot(
        self, octobot_with_mocks
    ):
        """Verifies exchange_producer and community_bot are called with correct arguments."""
        octobot = octobot_with_mocks["octobot"]
        community_bot = octobot_with_mocks["community_bot"]
        exchange_producer = octobot_with_mocks["exchange_producer"]

        await octobot.stop_all_trading_modes_and_pause_traders(
            stop_reason=commons_enums.StopReason.STOP_CONDITION_TRIGGERED,
            execution_details=None,
        )

        exchange_producer.stop_all_trading_modes_and_pause_trader.assert_awaited_once_with(
            None
        )
        community_bot.schedule_bot_stop.assert_awaited_once_with(
            commons_enums.StopReason.STOP_CONDITION_TRIGGERED
        )
        community_bot.insert_stopped_strategy_execution_log.assert_not_called()

    async def test_stop_all_trading_modes_and_pause_traders_with_execution_details_inserts_log(
        self, octobot_with_mocks
    ):
        """When execution_details is provided, insert_stopped_strategy_execution_log is called."""
        octobot = octobot_with_mocks["octobot"]
        community_bot = octobot_with_mocks["community_bot"]
        exchange_producer = octobot_with_mocks["exchange_producer"]

        execution_details = ExecutionDetails(
            timestamp=1000.0,
            description="Holding threshold exceeded",
            source=None,
        )

        await octobot.stop_all_trading_modes_and_pause_traders(
            stop_reason=commons_enums.StopReason.STOP_CONDITION_TRIGGERED,
            execution_details=execution_details,
        )

        exchange_producer.stop_all_trading_modes_and_pause_trader.assert_awaited_once_with(
            execution_details
        )
        community_bot.insert_stopped_strategy_execution_log.assert_awaited_once_with(
            "Holding threshold exceeded"
        )

    async def test_stop_all_trading_modes_and_pause_traders_continues_when_exchange_producer_raises(
        self, octobot_with_mocks
    ):
        """Schedule_bot_stop is still called when exchange_producer raises."""
        octobot = octobot_with_mocks["octobot"]
        community_bot = octobot_with_mocks["community_bot"]
        exchange_producer = octobot_with_mocks["exchange_producer"]

        exchange_producer.stop_all_trading_modes_and_pause_trader = AsyncMock(
            side_effect=RuntimeError("stop error")
        )

        await octobot.stop_all_trading_modes_and_pause_traders(
            stop_reason=commons_enums.StopReason.INVALID_CONFIG,
            execution_details=None,
        )

        community_bot.schedule_bot_stop.assert_awaited_once_with(
            commons_enums.StopReason.INVALID_CONFIG
        )

    async def test_stop_all_trading_modes_and_pause_traders_continues_when_schedule_bot_stop_raises(
        self, octobot_with_mocks
    ):
        """insert_log is still called when schedule_bot_stop raises (when execution_details is set)."""
        octobot = octobot_with_mocks["octobot"]
        community_bot = octobot_with_mocks["community_bot"]
        community_bot.schedule_bot_stop = AsyncMock(
            side_effect=ConnectionError("network error")
        )

        execution_details = ExecutionDetails(
            timestamp=2000.0,
            description="Volatility threshold exceeded",
            source=None,
        )

        await octobot.stop_all_trading_modes_and_pause_traders(
            stop_reason=commons_enums.StopReason.STOP_CONDITION_TRIGGERED,
            execution_details=execution_details,
        )

        community_bot.insert_stopped_strategy_execution_log.assert_awaited_once_with(
            "Volatility threshold exceeded"
        )
