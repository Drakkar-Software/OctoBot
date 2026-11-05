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
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import os

import aiohttp
import mock
import pytest

import octobot.constants as octobot_constants
import tentacles.Evaluator.Strategies.ai_strategies_evaluator as ai_strategies_evaluator
import tentacles.Evaluator.Strategies.drex_strategy_evaluator as drex_strategy_evaluator

pytestmark = pytest.mark.asyncio

AGGREGATED_DATA = {
    "TA": [{"eval_note": -1, "eval_note_description": ""}, {"eval_note": -0.6, "eval_note_description": ""}],
    "SOCIAL": [{"eval_note": 0.4, "eval_note_description": "Overall news sentiment: POSITIVE"}],
}
RUN_ARGS = (AGGREGATED_DATA, ["REAL_TIME"], "ai_service")


@pytest.fixture(params=[
    drex_strategy_evaluator.CryptoDrexStrategyEvaluator, drex_strategy_evaluator.GlobalDrexStrategyEvaluator
])
def strategy(request):
    return request.param(mock.Mock(is_tentacle_activated=mock.Mock(return_value=True)))


def _drex_post(answers):
    post = mock.MagicMock()
    post.return_value.__aenter__.return_value = mock.Mock(
        raise_for_status=mock.Mock(), json=mock.AsyncMock(return_value={"answers": answers})
    )
    return post


def _llm_agents():
    return mock.patch.object(ai_strategies_evaluator.ai_strategies.BaseLLMAIStrategyEvaluator, "_run_agents_analysis",
                             mock.AsyncMock(return_value=(0.1, "LLM summary")))


async def test_run_agents_analysis_uses_drex(strategy):
    post = _drex_post({"stance": {
        "type": "score", "score": 3.25, "probabilities": {"0": 0.0, "1": 0.0, "2": 0.05, "3": 0.65, "4": 0.3}
    }})
    with mock.patch.dict(os.environ, {"NACE_API_KEY": "key"}), \
            mock.patch.object(aiohttp.ClientSession, "post", post), _llm_agents() as llm_mock:
        assert await strategy._run_agents_analysis(*RUN_ARGS) == (
            0.625, "Drex: Buy (Strong sell 0%, Sell 0%, Neutral 5%, Buy 65%, Strong buy 30%)"
        )
        llm_mock.assert_not_called()
    assert post.call_args.kwargs["headers"] == {
        "Authorization": "Bearer key",
        "X-Nace-Client": f"octobot/{octobot_constants.LONG_VERSION}",
        "User-Agent": f"octobot/{octobot_constants.LONG_VERSION}",
    }
    state = post.call_args.kwargs["json"]["state"]
    assert state["evaluations by evaluator type"] == AGGREGATED_DATA
    assert list(state["eval_note meaning by evaluator type"]) == ["TA", "SOCIAL"]
    assert state["missing evaluator types"] == ["REAL_TIME"]


async def test_run_agents_analysis_falls_back_to_llm_agents_on_drex_error(strategy):
    for post in (
        mock.Mock(side_effect=aiohttp.ClientConnectionError()),
        mock.Mock(side_effect=TimeoutError()),
        _drex_post({"other": {}}),
    ):
        with mock.patch.dict(os.environ, {"NACE_API_KEY": "key"}), \
                mock.patch.object(aiohttp.ClientSession, "post", post), \
                mock.patch.object(strategy, "logger", mock.Mock()) as logger_mock, _llm_agents() as llm_mock:
            assert await strategy._run_agents_analysis(*RUN_ARGS) == (0.1, "LLM summary")
            llm_mock.assert_awaited_once_with(*RUN_ARGS)
            logger_mock.warning.assert_called_once()


async def test_run_agents_analysis_without_key_only_uses_llm_agents(strategy):
    with mock.patch.dict(os.environ), mock.patch.object(aiohttp.ClientSession, "post", mock.Mock()) as post, \
            _llm_agents() as llm_mock:
        os.environ.pop("NACE_API_KEY", None)
        assert await strategy._run_agents_analysis(*RUN_ARGS) == (0.1, "LLM summary")
        llm_mock.assert_awaited_once_with(*RUN_ARGS)
        post.assert_not_called()
