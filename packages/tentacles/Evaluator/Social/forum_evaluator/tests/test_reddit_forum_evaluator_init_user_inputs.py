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

import octobot_commons.constants as commons_constants
import tentacles.Evaluator.Social as Social
import tentacles.Evaluator.Social.forum_evaluator.forum as forum_module
import tests.test_utils.config as test_utils_config


def _create_forum_evaluator(specific_config: dict) -> Social.RedditForumEvaluator:
    evaluator = Social.RedditForumEvaluator(test_utils_config.load_test_tentacles_config())
    evaluator.specific_config = specific_config
    return evaluator


class TestRedditForumEvaluatorInitUserInputs:
    def test_seeds_default_cryptocurrency_when_config_empty(self):
        evaluator = _create_forum_evaluator({})
        evaluator.init_user_inputs({})

        cryptocurrencies = evaluator.specific_config[commons_constants.CONFIG_CRYPTO_CURRENCIES]
        assert len(cryptocurrencies) == 1
        assert cryptocurrencies[0][commons_constants.CONFIG_CRYPTO_CURRENCY] == "Bitcoin"
        assert cryptocurrencies[0][forum_module.CONFIG_REDDIT_SUBREDDITS] == ["Bitcoin"]

    def test_preserves_existing_user_cryptocurrencies(self):
        user_cryptocurrencies = [
            {
                commons_constants.CONFIG_CRYPTO_CURRENCY: "Ethereum",
                forum_module.CONFIG_REDDIT_SUBREDDITS: ["ethereum"],
            },
            {
                commons_constants.CONFIG_CRYPTO_CURRENCY: "NEO",
                forum_module.CONFIG_REDDIT_SUBREDDITS: ["NEO"],
            },
        ]
        evaluator = _create_forum_evaluator(
            {
                commons_constants.CONFIG_CRYPTO_CURRENCIES: copy.deepcopy(user_cryptocurrencies),
            }
        )
        evaluator.init_user_inputs({})

        cryptocurrencies = evaluator.specific_config[commons_constants.CONFIG_CRYPTO_CURRENCIES]
        assert len(cryptocurrencies) == 2
        assert cryptocurrencies[0][commons_constants.CONFIG_CRYPTO_CURRENCY] == "Ethereum"
        assert cryptocurrencies[0][forum_module.CONFIG_REDDIT_SUBREDDITS] == ["ethereum"]
        assert cryptocurrencies[1][commons_constants.CONFIG_CRYPTO_CURRENCY] == "NEO"
        assert cryptocurrencies[1][forum_module.CONFIG_REDDIT_SUBREDDITS] == ["NEO"]
