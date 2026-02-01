#  Drakkar-Software OctoBot-Tentacles
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
#  You should have received a copy of the GNU Lesser General
#  License along with this library.
import pytest
from unittest import mock

import octobot_trading.enums as trading_enums
import tentacles.Trading.Mode.ai_trading_mode.ai_index_trading as ai_index_trading
import tentacles.Trading.Mode.ai_trading_mode.ai_index_distribution as ai_index_distribution

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mode():
    """Create a minimal AIIndexTradingMode instance."""
    mock_exchange_manager = mock.Mock()
    mock_exchange_manager.is_backtesting = True
    mode = ai_index_trading.AIIndexTradingMode({"fallback_distribution": []}, mock_exchange_manager)
    return mode


@pytest.fixture
def consumer(mode):
    """Create a consumer instance."""
    return ai_index_trading.AIIndexTradingModeConsumer(mode)


async def test_mode_has_producers_and_consumers(mode):
    """Test AIIndexTradingMode has required classes."""
    assert ai_index_trading.AIIndexTradingModeProducer in mode.MODE_PRODUCER_CLASSES
    assert ai_index_trading.AIIndexTradingModeConsumer in mode.MODE_CONSUMER_CLASSES


async def test_consumer_processes_ai_instructions(consumer):
    """Test consumer applies AI instructions before rebalancing."""
    consumer.trading_mode = mock.Mock()
    consumer.trading_mode._rebalance_portfolio = mock.AsyncMock(return_value=[])
    consumer.trading_mode.is_processing_rebalance = False

    with mock.patch.object(ai_index_distribution, "apply_ai_instructions") as mock_apply:
        await consumer.create_new_orders(
            symbol="BTC/USDT",
            final_note=0.0,
            state=trading_enums.EvaluatorStates.NEUTRAL.value,
            **{"data": {"ai_instructions": [{"action": "test"}]}},
        )

        mock_apply.assert_called_once_with(consumer.trading_mode, [{"action": "test"}])
        consumer.trading_mode._rebalance_portfolio.assert_called_once()


async def test_consumer_handles_missing_ai_instructions(consumer):
    """Test consumer handles missing AI instructions gracefully."""
    consumer.trading_mode = mock.Mock()
    consumer.trading_mode._rebalance_portfolio = mock.AsyncMock(return_value=[])
    consumer.trading_mode.is_processing_rebalance = False

    with mock.patch.object(ai_index_distribution, "apply_ai_instructions") as mock_apply:
        await consumer.create_new_orders(
            symbol="BTC/USDT",
            final_note=0.0,
            state=trading_enums.EvaluatorStates.NEUTRAL.value,
            **{"data": {}},
        )

        mock_apply.assert_not_called()
        consumer.trading_mode._rebalance_portfolio.assert_called_once()
