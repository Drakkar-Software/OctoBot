#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import asyncio
import typing

import octobot_commons.enums as common_enums

import octobot_trading.api as trading_api
import octobot_trading.octobot_channel_consumer as trading_channel_consumer

import octobot.channels as octobot_channel
import octobot.automation as automation


class ExchangeProducer(octobot_channel.OctoBotChannelProducer):
    def __init__(self, channel, octobot, backtesting, ignore_config=False):
        super().__init__(channel)
        self.octobot = octobot
        self.ignore_config = ignore_config

        self.backtesting = backtesting
        self.exchange_manager_ids: list[str] = []

        self.to_create_exchanges_count: int = 0
        self.created_all_exchanges: asyncio.Event = asyncio.Event()
        
    async def start(self):
        self.to_create_exchanges_count = 0
        self.created_all_exchanges.clear()
        for exchange_name in trading_api.get_enabled_exchanges_names(self.octobot.config):
            await self.create_exchange(exchange_name, self.backtesting)
            self.to_create_exchanges_count += 1

    def register_created_exchange_id(self, exchange_id):
        self.exchange_manager_ids.append(exchange_id)
        if len(self.exchange_manager_ids) == self.to_create_exchanges_count:
            self.created_all_exchanges.set()
            self.logger.debug(f"Exchange(s) created")

    def are_all_trading_modes_stoppped_and_traders_paused(self) -> bool:
        return all(
            trading_api.are_all_trading_modes_stoppped_and_trader_paused(exchange_manager)
            for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(
                self.exchange_manager_ids
            )
        )

    async def stop_all_trading_modes_and_pause_traders(
        self, execution_details: typing.Optional[automation.ExecutionDetails]
    ):
        for exchange_id in self.exchange_manager_ids:
            await self._stop_exchange_trading_modes_and_pause_trader(exchange_id, execution_details)
            
    async def _stop_exchange_trading_modes_and_pause_trader(
        self, exchange_id: str, execution_details: typing.Optional[automation.ExecutionDetails]
    ):
        await self.send(
            bot_id=self.octobot.bot_id,
            subject=common_enums.OctoBotChannelSubjects.UPDATE.value,
            action=trading_channel_consumer.OctoBotChannelTradingActions.STOP_EXCHANGE_TRADING_MODES_AND_PAUSE_TRADER.value,
            data={
                trading_channel_consumer.OctoBotChannelTradingDataKeys.EXCHANGE_ID.value: exchange_id,
                trading_channel_consumer.OctoBotChannelTradingDataKeys.REASON.value: execution_details.description if execution_details else None,
            }
        )

    async def stop(self):
        self.logger.debug("Stopping ...")
        for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(self.exchange_manager_ids):
            await trading_api.stop_exchange(exchange_manager)
        self.logger.debug("Stopped")

    async def create_exchange(self, exchange_name, backtesting):
        await self.send(
            bot_id=self.octobot.bot_id,
            subject=common_enums.OctoBotChannelSubjects.CREATION.value,
            action=trading_channel_consumer.OctoBotChannelTradingActions.EXCHANGE.value,
            data={
                trading_channel_consumer.OctoBotChannelTradingDataKeys.TENTACLES_SETUP_CONFIG.value:
                    self.octobot.tentacles_setup_config,
                trading_channel_consumer.OctoBotChannelTradingDataKeys.MATRIX_ID.value:
                    self.octobot.evaluator_producer.matrix_id,
                trading_channel_consumer.OctoBotChannelTradingDataKeys.ENABLE_REALTIME_DATA_FETCHING.value: 
                    self.octobot.evaluator_producer.has_real_time_evaluators_configured,
                trading_channel_consumer.OctoBotChannelTradingDataKeys.BACKTESTING.value: backtesting,
                trading_channel_consumer.OctoBotChannelTradingDataKeys.EXCHANGE_CONFIG.value:
                    self.octobot.config,
                trading_channel_consumer.OctoBotChannelTradingDataKeys.EXCHANGE_NAME.value: exchange_name,
            }
        )
