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

import pytest
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_services.constants as services_constants
import tentacles.Evaluator.Social as Social
import tests.test_utils.config as test_utils_config

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def _trigger_callback_with_data_and_assert_note(evaluator: Social.TelegramChannelSignalEvaluator,
                                                      data=None,
                                                      note=commons_constants.START_PENDING_EVAL_NOTE):
    await evaluator._feed_callback(data)
    assert evaluator.eval_note == note
    evaluator.eval_note = commons_constants.START_PENDING_EVAL_NOTE


def _create_evaluator_with_supported_channel_signals():
    evaluator = Social.TelegramChannelSignalEvaluator(test_utils_config.load_test_tentacles_config())
    evaluator.logger = logging.get_logger(evaluator.get_name())
    evaluator.specific_config = {
        "telegram-channels": [
            {
                "channel_name": "TEST-CHAN-1",
                "signal_pattern": {
                    "MARKET_BUY": "Side: (BUY)",
                    "MARKET_SELL": "Side: (SELL)"
                },
                "signal_pair": "Pair: (.*)"
            },
            {
                "channel_name": "TEST-CHAN-2",
                "signal_pattern": {
                    "MARKET_BUY": ".* : (-1)$",
                    "MARKET_SELL": ".* : (1)$"
                },
                "signal_pair": "(.*):"
            }
        ]
    }
    evaluator.init_user_inputs({})
    evaluator.eval_note = commons_constants.START_PENDING_EVAL_NOTE
    return evaluator


async def test_without_data():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator)


async def test_with_empty_data():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={})


async def test_incorrect_signal_without_sender_without_channel_message():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: False,
        services_constants.CONFIG_MESSAGE_SENDER: "",
        services_constants.CONFIG_MESSAGE_CONTENT: "",
    })


async def test_incorrect_signal_without_sender_with_channel_message():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "",
        services_constants.CONFIG_MESSAGE_CONTENT: "",
    })


async def test_incorrect_signal_chan1_without_content():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-1",
        services_constants.CONFIG_MESSAGE_CONTENT: "",
    })


async def test_incorrect_signal_chan1_without_coin():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-1",
        services_constants.CONFIG_MESSAGE_CONTENT: """
        Order Id: 1631033831358699
        Pair: 
        Side:
        Price: 12.909
        """,
    })


async def test_incorrect_signal_chan1_without_separator():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-1",
        services_constants.CONFIG_MESSAGE_CONTENT: """
        Order Id: 1631033831358699
        Pair QTUMUSDT
        Side: BUY
        Price: 12.909
        """,
    })


async def test_correct_signal_chan1_with_not_channel_message():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: False,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-1",
        services_constants.CONFIG_MESSAGE_CONTENT: """
        Order Id: 1631033831358699
        Pair: QTUMUSDT
        Side: BUY
        Price: 12.909
        """,
    })


async def test_correct_signal_chan1_with_chan2():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-2",
        services_constants.CONFIG_MESSAGE_CONTENT: """
        Order Id: 1631033831358699
        Pair: QTUMUSDT
        Side: BUY
        Price: 12.909
        """,
    })


async def test_correct_signal_chan1():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-1",
        services_constants.CONFIG_MESSAGE_CONTENT: """
        Order Id: 1631033831358699
        Pair: QTUMUSDT
        Side: BUY
        Price: 12.909
        """,
    }, note=-1)


async def test_correct_signal_chan2_but_with_chan1():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-1",
        services_constants.CONFIG_MESSAGE_CONTENT: "BTC/USDT : 1",
    })


async def test_correct_signal_chan2():
    evaluator = _create_evaluator_with_supported_channel_signals()
    await _trigger_callback_with_data_and_assert_note(evaluator, data={
        services_constants.CONFIG_IS_CHANNEL_MESSAGE: True,
        services_constants.CONFIG_MESSAGE_SENDER: "TEST-CHAN-2",
        services_constants.CONFIG_MESSAGE_CONTENT: "BTC/USDT : -1",
    }, note=-1)
