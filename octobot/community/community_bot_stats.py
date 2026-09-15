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

"""Periodic community bot config/stats updates.

``CommunityBotStats`` is temporary until full migration to OctoBot v3 replaces this path.
"""

import asyncio

import octobot_commons.logging as logging
import octobot_commons.authentication as authentication
import octobot_commons.constants as common_constants

import octobot_trading.api as trading_api


class CommunityBotStats:

    def __init__(self, octobot_api):
        self.octobot_api = octobot_api
        self.logger = logging.get_logger(self.__class__.__name__)
        self.keep_running = True
        self.task_enabled = False

    async def start_community_task(self):
        try:
            while self.keep_running:
                await asyncio.sleep(common_constants.TIMER_BETWEEN_METRICS_UPTIME_UPDATE)
                try:
                    await self._update_authenticated_bot()
                except Exception as err:
                    self.logger.debug(f"Exception when handling community data : {err}")
        except asyncio.CancelledError:
            pass
        except Exception as err:
            self.logger.debug(f"Exception when handling community registration: {err}")

    async def stop_task(self):
        self.logger.debug("Stopping ...")
        self.keep_running = False
        self.logger.debug("Stopped ...")

    async def _update_authenticated_bot(self):
        try:
            if authentication.Authenticator.instance().is_logged_in():
                await authentication.Authenticator.instance().update_bot_config_and_stats(
                    self._get_profitability()
                )
        except Exception as err:
            self.logger.debug(f"Exception when pushing config and stats : {err}")

    def _get_profitability(self):
        total_origin_values = 0
        total_profitability = 0

        for exchange_manager in self._get_exchange_managers():
            if trading_api.is_exchange_trading(exchange_manager):
                profitability, _, _, _, _ = trading_api.get_profitability_stats(exchange_manager)
                total_profitability += float(profitability)
                total_origin_values += float(trading_api.get_origin_portfolio_value(exchange_manager))

        return (total_profitability * 100 / total_origin_values) if total_origin_values > 0 else 0

    def _get_exchange_managers(self):
        return trading_api.get_exchange_managers_from_exchange_ids(
            self.octobot_api.get_exchange_manager_ids()
        )
