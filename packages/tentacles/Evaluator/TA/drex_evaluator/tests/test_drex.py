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
import multidict
import pytest
import yarl

import octobot.constants as octobot_constants
import octobot_commons.enums as commons_enums

import tentacles.Evaluator.TA.ai_evaluator as ai_evaluator
import tentacles.Evaluator.TA.drex_evaluator as drex_evaluator

pytestmark = pytest.mark.asyncio

ASK_GPT_ARGS = ("preprompt", "1, 2, 3", "BTC/USDT", "4h", 1730000000)


@pytest.fixture
def drex_eval():
    evaluator = drex_evaluator.DrexEvaluator(mock.Mock(is_tentacle_activated=mock.Mock(return_value=True)))
    evaluator.indicator = next(iter(evaluator.INDICATORS))
    evaluator.source = evaluator.SOURCES[3]
    return evaluator


def _drex_post(answers):
    post = mock.MagicMock()
    post.return_value.__aenter__.return_value = mock.Mock(
        raise_for_status=mock.Mock(), json=mock.AsyncMock(return_value={"answers": answers})
    )
    return post


async def test_ask_gpt_uses_drex(drex_eval):
    post = _drex_post({"up": {"type": "noul", "noul": 0.7312}})
    with mock.patch.dict(os.environ, {"NACE_API_KEY": "key"}), \
            mock.patch.object(aiohttp.ClientSession, "post", post), \
            mock.patch.object(ai_evaluator.GPTEvaluator, "ask_gpt", mock.AsyncMock()) as gpt_mock:
        answer = await drex_eval.ask_gpt(*ASK_GPT_ARGS)
        gpt_mock.assert_not_called()
    assert answer == "up 73%"
    assert drex_eval._parse_prediction_side(answer) == -1
    assert drex_eval._parse_confidence(answer) == 73
    assert post.call_args.kwargs["headers"] == {
        "Authorization": "Bearer key",
        "X-Nace-Client": f"octobot/{octobot_constants.LONG_VERSION}",
        "User-Agent": f"octobot/{octobot_constants.LONG_VERSION}",
    }
    assert post.call_args.kwargs["json"]["state"]["data (oldest first)"] == "1, 2, 3"

    with mock.patch.dict(os.environ, {"NACE_API_KEY": "key"}), \
            mock.patch.object(aiohttp.ClientSession, "post", _drex_post({"up": {"type": "noul", "noul": 0.2}})):
        answer = await drex_eval.ask_gpt(*ASK_GPT_ARGS)
    assert answer == "down 80%"
    assert drex_eval._parse_prediction_side(answer) == 1
    assert drex_eval._parse_confidence(answer) == 80


async def test_ask_gpt_falls_back_to_gpt_on_drex_error(drex_eval):
    unauthorized = aiohttp.ClientResponseError(
        aiohttp.RequestInfo(yarl.URL("https://console.nace.ai/v1/systemone"), "POST",
                            multidict.CIMultiDictProxy(multidict.CIMultiDict(Authorization="Bearer key"))),
        (), status=401, message="Unauthorized"
    )
    for post in (
        mock.Mock(side_effect=aiohttp.ClientConnectionError()),
        mock.Mock(side_effect=TimeoutError()),
        mock.Mock(side_effect=unauthorized),
        _drex_post({"other": {}}),
    ):
        with mock.patch.dict(os.environ, {"NACE_API_KEY": "key"}), \
                mock.patch.object(aiohttp.ClientSession, "post", post), \
                mock.patch.object(drex_eval, "logger", mock.Mock()) as logger_mock, \
                mock.patch.object(ai_evaluator.GPTEvaluator, "ask_gpt",
                                  mock.AsyncMock(return_value="down 60%")) as gpt_mock:
            assert await drex_eval.ask_gpt(*ASK_GPT_ARGS) == "down 60%"
            gpt_mock.assert_awaited_once_with(*ASK_GPT_ARGS)
            logger_mock.warning.assert_called_once()
            assert "Bearer" not in logger_mock.warning.call_args.args[0]


async def test_ask_gpt_without_key_only_uses_gpt(drex_eval):
    with mock.patch.dict(os.environ), \
            mock.patch.object(aiohttp.ClientSession, "post", mock.Mock()) as post, \
            mock.patch.object(ai_evaluator.GPTEvaluator, "ask_gpt",
                              mock.AsyncMock(return_value="up 70%")) as gpt_mock:
        os.environ.pop("NACE_API_KEY", None)
        assert await drex_eval.ask_gpt(*ASK_GPT_ARGS) == "up 70%"
        gpt_mock.assert_awaited_once_with(*ASK_GPT_ARGS)
        post.assert_not_called()


async def test_get_signals_history_type():
    with mock.patch.dict(os.environ, {"NACE_API_KEY": "key"}):
        assert drex_evaluator.DrexEvaluator.get_signals_history_type() is None
    with mock.patch.dict(os.environ):
        os.environ.pop("NACE_API_KEY", None)
        assert drex_evaluator.DrexEvaluator.get_signals_history_type() is commons_enums.SignalHistoryTypes.GPT
