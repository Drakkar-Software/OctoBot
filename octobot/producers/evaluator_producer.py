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
from octobot.channels.octobot_channel import OctoBotChannelProducer
from octobot.logger import init_evaluator_chan_logger
from octobot_backtesting.api.backtesting import is_backtesting_enabled
from octobot_commons.enums import OctoBotChannelSubjects
from octobot_evaluators.api.evaluators import initialize_evaluators
from octobot_evaluators.api.initialization import create_evaluator_channels
from octobot_evaluators.consumers.octobot_channel_consumer import OctoBotChannelEvaluatorActions as EvaluatorActions, \
    OctoBotChannelEvaluatorDataKeys as EvaluatorKeys


class EvaluatorProducer(OctoBotChannelProducer):
    """EvaluatorFactory class:
    - Create evaluators
    """

    def __init__(self, channel, octobot):
        super().__init__(channel)
        self.octobot = octobot
        self.tentacles_setup_config = self.octobot.tentacles_setup_config

        self.matrix_id = None

    async def start(self):
        self.matrix_id = await initialize_evaluators(self.octobot.config, self.tentacles_setup_config)
        await create_evaluator_channels(self.matrix_id, is_backtesting=is_backtesting_enabled(self.octobot.config))
        await init_evaluator_chan_logger(self.matrix_id)

    async def create_evaluators(self, exchange_configuration):
        await self.send(bot_id=self.octobot.bot_id,
                        subject=OctoBotChannelSubjects.CREATION.value,
                        action=EvaluatorActions.EVALUATOR.value,
                        data={
                            EvaluatorKeys.TENTACLES_SETUP_CONFIG.value: self.octobot.tentacles_setup_config,
                            EvaluatorKeys.MATRIX_ID.value: self.octobot.evaluator_producer.matrix_id,
                            EvaluatorKeys.EXCHANGE_CONFIGURATION.value: exchange_configuration
                        })


