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
from mock import patch, AsyncMock, Mock

from octobot.automation.bases.execution_details import ExecutionDetails
from octobot.producers.exchange_producer import ExchangeProducer


pytestmark = pytest.mark.asyncio


@pytest.fixture
def exchange_producer():
    """ExchangeProducer with default exchange_manager_ids for stop_all_trading_modes tests."""
    producer = ExchangeProducer(object(), object(), backtesting=False)
    producer.exchange_manager_ids = ["exchange_1"]
    return producer


class TestExchangeProducerStopAllTradingModesAndPauseTrader:
    async def test_stop_all_trading_modes_and_pause_trader_with_no_trading_modes(
        self, exchange_producer
    ):
        """When exchange has no trading modes, only set_trading_enabled(False) is called."""
        mock_exchange_manager = object()

        with patch("octobot.producers.exchange_producer.trading_api") as mock_trading_api:
            mock_trading_api.get_exchange_managers_from_exchange_ids.return_value = [
                mock_exchange_manager
            ]
            mock_trading_api.get_trading_modes.return_value = []

            await exchange_producer.stop_all_trading_modes_and_pause_trader(execution_details=None)

            mock_trading_api.get_exchange_managers_from_exchange_ids.assert_called_once_with(
                ["exchange_1"]
            )
            mock_trading_api.get_trading_modes.assert_called_once_with(mock_exchange_manager)
            mock_trading_api.set_trading_enabled.assert_called_once_with(
                mock_exchange_manager, False
            )
            mock_trading_api.stop_strategy_execution.assert_not_called()

    async def test_stop_all_trading_modes_and_pause_trader_with_trading_modes(
        self, exchange_producer
    ):
        """When exchange has trading modes, stops each and disables trading."""
        mock_exchange_manager = object()
        mock_trading_mode_1 = object()
        mock_trading_mode_2 = object()

        with patch("octobot.producers.exchange_producer.trading_api") as mock_trading_api:
            mock_trading_api.get_exchange_managers_from_exchange_ids.return_value = [
                mock_exchange_manager
            ]
            mock_trading_api.get_trading_modes.return_value = [
                mock_trading_mode_1,
                mock_trading_mode_2,
            ]
            mock_trading_api.get_exchange_name.return_value = "binance"
            mock_trading_api.stop_strategy_execution = AsyncMock()

            await exchange_producer.stop_all_trading_modes_and_pause_trader(execution_details=None)

            mock_trading_api.get_exchange_managers_from_exchange_ids.assert_called_once_with(
                ["exchange_1"]
            )
            mock_trading_api.get_trading_modes.assert_called_once_with(mock_exchange_manager)
            mock_trading_api.get_exchange_name.assert_called_once_with(mock_exchange_manager)
            assert mock_trading_api.stop_strategy_execution.call_count == 2
            mock_trading_api.stop_strategy_execution.assert_any_call(
                mock_trading_mode_1, None
            )
            mock_trading_api.stop_strategy_execution.assert_any_call(
                mock_trading_mode_2, None
            )
            mock_trading_api.set_trading_enabled.assert_called_once_with(
                mock_exchange_manager, False
            )

    async def test_stop_all_trading_modes_and_pause_trader_with_execution_details(
        self, exchange_producer
    ):
        """When execution_details is provided, description is passed to stop_strategy_execution."""
        mock_exchange_manager = object()
        mock_trading_mode = object()
        execution_details = ExecutionDetails(
            timestamp=1000.0,
            description="Holding threshold exceeded",
            source=None,
        )

        with patch("octobot.producers.exchange_producer.trading_api") as mock_trading_api:
            mock_trading_api.get_exchange_managers_from_exchange_ids.return_value = [
                mock_exchange_manager
            ]
            mock_trading_api.get_trading_modes.return_value = [mock_trading_mode]
            mock_trading_api.get_exchange_name.return_value = "binance"
            mock_trading_api.stop_strategy_execution = AsyncMock()

            await exchange_producer.stop_all_trading_modes_and_pause_trader(
                execution_details=execution_details
            )

            mock_trading_api.stop_strategy_execution.assert_called_once_with(
                mock_trading_mode, "Holding threshold exceeded"
            )

    async def test_stop_all_trading_modes_and_pause_trader_multiple_exchanges(
        self, exchange_producer
    ):
        """Handles multiple exchange managers correctly."""
        exchange_producer.exchange_manager_ids = ["exchange_1", "exchange_2"]

        mock_manager_1 = object()
        mock_manager_2 = object()
        mock_trading_mode = object()

        with patch("octobot.producers.exchange_producer.trading_api") as mock_trading_api:
            mock_trading_api.get_exchange_managers_from_exchange_ids.return_value = [
                mock_manager_1,
                mock_manager_2,
            ]
            mock_trading_api.get_trading_modes.side_effect = [
                [mock_trading_mode],
                [],
            ]
            mock_trading_api.get_exchange_name.return_value = "binance"
            mock_trading_api.stop_strategy_execution = AsyncMock()

            await exchange_producer.stop_all_trading_modes_and_pause_trader(execution_details=None)

            mock_trading_api.get_exchange_managers_from_exchange_ids.assert_called_once_with(
                ["exchange_1", "exchange_2"]
            )
            assert mock_trading_api.get_trading_modes.call_count == 2
            mock_trading_api.stop_strategy_execution.assert_called_once_with(
                mock_trading_mode, None
            )
            assert mock_trading_api.set_trading_enabled.call_count == 2
            mock_trading_api.set_trading_enabled.assert_any_call(mock_manager_1, False)
            mock_trading_api.set_trading_enabled.assert_any_call(mock_manager_2, False)
