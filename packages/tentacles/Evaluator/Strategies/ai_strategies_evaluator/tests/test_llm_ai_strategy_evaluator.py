#  Drakkar-Software OctoBot
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
import pytest
from unittest.mock import AsyncMock, patch

import tentacles.Evaluator.Strategies as Strategies
import tentacles.Trading.Mode as Mode
import octobot_services.api.services as services_api
from octobot_services.services.gpt_service import GPTService
from octobot_evaluators.enums import EvaluatorMatrixTypes

import tests.functional_tests.strategy_evaluators_tests.abstract_strategy_test as abstract_strategy_test

pytestmark = pytest.mark.asyncio


@pytest.fixture
def strategy_tester():
    """Create a strategy tester instance."""
    tester = LLMAIStrategyEvaluatorTest()
    tester.initialize(Strategies.LLMAIStrategyEvaluator, Mode.DailyTradingMode)
    return tester


class LLMAIStrategyEvaluatorTest(abstract_strategy_test.AbstractStrategyTest):
    """Test suite for LLMAIStrategyEvaluator."""

    async def test_agents_execute(self):
        """Test that agents execute and return results."""
        evaluator = Strategies.LLMAIStrategyEvaluator(self.tentacles_setup_config)
        mock_llm_service = AsyncMock(spec=GPTService)

        with patch.object(services_api, "get_service", new_callable=AsyncMock) as mock_get_service:
            mock_get_service.return_value = mock_llm_service

            # Mock agents
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = {
                "eval_note": 0.7,
                "eval_note_description": "Test analysis",
                "confidence": 85,
            }

            with (
                patch("ai_strategies.AgentFactory.create_agent_for_evaluator_type") as mock_create,
                patch("ai_strategies.AgentFactory.create_summarization_agent") as mock_summary,
            ):
                mock_create.return_value = mock_agent
                mock_summary.return_value = mock_agent

                await evaluator.matrix_callback(
                    matrix_id="test",
                    evaluator_name="test",
                    evaluator_type=EvaluatorMatrixTypes.TA.value,
                    eval_note=0.7,
                    eval_note_type="",
                    eval_note_description="",
                    eval_note_metadata={},
                    exchange_name="binance",
                    cryptocurrency="BTC",
                    symbol="BTC/USDT",
                    time_frame="1h",
                )

                assert mock_create.called
                assert mock_agent.execute.called


async def test_bullish_evaluation(strategy_tester):
    """Test bullish evaluation."""
    await strategy_tester.test_agents_execute()


async def test_bearish_evaluation(strategy_tester):
    """Test bearish evaluation."""
    await strategy_tester.test_agents_execute()


async def test_neutral_evaluation(strategy_tester):
    """Test neutral evaluation."""
    await strategy_tester.test_agents_execute()
