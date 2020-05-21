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
from octobot_commons.constants import CONFIG_ENABLED_OPTION
from octobot_trading.constants import CONFIG_EXCHANGES

from octobot.channels.octobot_channel import OctoBotChannelProducer
from octobot_commons.enums import OctoBotChannelSubjects
from octobot_trading.consumers.octobot_channel_consumer import OctoBotChannelTradingActions as TradingActions, \
    OctoBotChannelTradingDataKeys as TradingKeys


class ExchangeProducer(OctoBotChannelProducer):
    def __init__(self, channel, octobot, backtesting, ignore_config=False):
        super().__init__(channel)
        self.octobot = octobot
        self.ignore_config = ignore_config

        self.backtesting = backtesting
        self.exchange_manager_ids = []

    async def start(self):
        for exchange_name in self.octobot.config[CONFIG_EXCHANGES]:
            if self.octobot.config[CONFIG_EXCHANGES][exchange_name].get(CONFIG_ENABLED_OPTION, True):
                await self.create_exchange(exchange_name, self.backtesting)

    async def create_exchange(self, exchange_name, backtesting):
        await self.send(bot_id=self.octobot.bot_id,
                        subject=OctoBotChannelSubjects.CREATION.value,
                        action=TradingActions.EXCHANGE.value,
                        data={
                            TradingKeys.TENTACLES_SETUP_CONFIG.value: self.octobot.tentacles_setup_config,
                            TradingKeys.MATRIX_ID.value: self.octobot.evaluator_producer.matrix_id,
                            TradingKeys.BACKTESTING.value: backtesting,
                            TradingKeys.EXCHANGE_CONFIG.value: self.octobot.config,
                            TradingKeys.EXCHANGE_NAME.value: exchange_name,
                        })
