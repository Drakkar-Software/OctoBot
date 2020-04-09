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
from octobot_commons.logging.logging_util import get_logger
from octobot_evaluators.api.evaluators import initialize_evaluators, create_all_type_evaluators
from octobot_evaluators.api.initialization import create_matrix_channels
from octobot_trading.exchanges.exchanges import Exchanges
from octobot.logger import init_evaluator_chan_logger


class EvaluatorFactory:
    """EvaluatorFactory class:
    - Create evaluators
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.matrix_id = None
        self.tentacles_setup_config = None

    async def initialize(self):
        self.tentacles_setup_config = self.octobot.tentacles_setup_config
        self.matrix_id = await initialize_evaluators(self.octobot.config, self.tentacles_setup_config)
        await create_matrix_channels()

    async def create(self):
        for exchange_configuration in Exchanges.instance().get_all_exchanges():
            await create_all_type_evaluators(
                self.octobot.config,
                tentacles_setup_config=self.tentacles_setup_config,
                matrix_id=self.matrix_id,
                exchange_name=exchange_configuration.exchange_name,
                bot_id=self.octobot.bot_id,
                symbols_by_crypto_currencies=exchange_configuration.symbols_by_crypto_currencies,
                symbols=exchange_configuration.symbols,
                time_frames=exchange_configuration.time_frames
            )
        await init_evaluator_chan_logger()
