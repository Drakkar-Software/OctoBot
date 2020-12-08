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
import octobot_commons.enums as common_enums

import octobot_backtesting.api as backtesting_api

import octobot_evaluators.api as evaluator_api
import octobot_evaluators.octobot_channel_consumer as evaluator_channel_consumer

import octobot.channels as octobot_channel
import octobot.logger as logger


class EvaluatorProducer(octobot_channel.OctoBotChannelProducer):
    """EvaluatorFactory class:
    - Create evaluators
    """

    def __init__(self, channel, octobot):
        super().__init__(channel)
        self.octobot = octobot
        self.tentacles_setup_config = self.octobot.tentacles_setup_config

        self.matrix_id = None

    async def start(self):
        self.matrix_id = await evaluator_api.initialize_evaluators(self.octobot.config, self.tentacles_setup_config)
        await evaluator_api.create_evaluator_channels(
            self.matrix_id, is_backtesting=backtesting_api.is_backtesting_enabled(self.octobot.config))
        await logger.init_evaluator_chan_logger(self.matrix_id)

    async def create_evaluators(self, exchange_configuration):
        await self.send(bot_id=self.octobot.bot_id,
                        subject=common_enums.OctoBotChannelSubjects.CREATION.value,
                        action=evaluator_channel_consumer.OctoBotChannelEvaluatorActions.EVALUATOR.value,
                        data={
                            evaluator_channel_consumer.OctoBotChannelEvaluatorDataKeys.TENTACLES_SETUP_CONFIG.value:
                                self.octobot.tentacles_setup_config,
                            evaluator_channel_consumer.OctoBotChannelEvaluatorDataKeys.MATRIX_ID.value:
                                self.octobot.evaluator_producer.matrix_id,
                            evaluator_channel_consumer.OctoBotChannelEvaluatorDataKeys.EXCHANGE_CONFIGURATION.value:
                                exchange_configuration
                        })


