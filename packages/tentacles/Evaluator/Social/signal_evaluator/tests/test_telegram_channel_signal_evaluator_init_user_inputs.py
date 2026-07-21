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
import copy

import octobot_services.constants as services_constants
import tentacles.Evaluator.Social as Social
import tests.test_utils.config as test_utils_config


def _create_signal_evaluator(specific_config: dict) -> Social.TelegramChannelSignalEvaluator:
    evaluator = Social.TelegramChannelSignalEvaluator(
        test_utils_config.load_test_tentacles_config()
    )
    evaluator.specific_config = specific_config
    return evaluator


class TestTelegramChannelSignalEvaluatorInitUserInputs:
    def test_seeds_default_channel_when_config_empty(self):
        evaluator = _create_signal_evaluator({})
        evaluator.init_user_inputs({})

        channels = evaluator.specific_config[services_constants.CONFIG_TELEGRAM_CHANNEL]
        assert len(channels) == 1
        channel = channels[0]
        assert channel[evaluator.SIGNAL_CHANNEL_NAME_KEY] == "Test-Channel"
        assert channel[evaluator.SIGNAL_PAIR_KEY] == "Pair: (.*)$"
        assert channel[evaluator.SIGNAL_PATTERN_KEY] == {
            evaluator.SIGNAL_PATTERN_MARKET_BUY_KEY: "Side: (BUY)$",
            evaluator.SIGNAL_PATTERN_MARKET_SELL_KEY: "Side: (SELL)$",
        }
        assert list(evaluator.channels_config_by_channel_name) == ["Test-Channel"]

    def test_preserves_existing_user_channels(self):
        channel_name_key = Social.TelegramChannelSignalEvaluator.SIGNAL_CHANNEL_NAME_KEY
        signal_pair_key = Social.TelegramChannelSignalEvaluator.SIGNAL_PAIR_KEY
        signal_pattern_key = Social.TelegramChannelSignalEvaluator.SIGNAL_PATTERN_KEY
        buy_key = Social.TelegramChannelSignalEvaluator.SIGNAL_PATTERN_MARKET_BUY_KEY
        sell_key = Social.TelegramChannelSignalEvaluator.SIGNAL_PATTERN_MARKET_SELL_KEY
        user_channels = [
            {
                channel_name_key: "My-Chan",
                signal_pair_key: "X:(.*)",
                signal_pattern_key: {
                    buy_key: "buy-regex",
                    sell_key: "sell-regex",
                },
            },
            {
                channel_name_key: "Other-Chan",
                signal_pair_key: "Y:(.*)",
                signal_pattern_key: {
                    buy_key: "other-buy",
                    sell_key: "other-sell",
                },
            },
        ]
        evaluator = _create_signal_evaluator(
            {
                services_constants.CONFIG_TELEGRAM_CHANNEL: copy.deepcopy(user_channels),
            }
        )
        evaluator.init_user_inputs({})

        channels = evaluator.specific_config[services_constants.CONFIG_TELEGRAM_CHANNEL]
        assert len(channels) == 2
        assert channels[0][channel_name_key] == "My-Chan"
        assert channels[0][signal_pair_key] == "X:(.*)"
        assert channels[0][signal_pattern_key] == {
            buy_key: "buy-regex",
            sell_key: "sell-regex",
        }
        assert channels[1][channel_name_key] == "Other-Chan"
        assert "Test-Channel" not in evaluator.channels_config_by_channel_name
        assert set(evaluator.channels_config_by_channel_name) == {"My-Chan", "Other-Chan"}
