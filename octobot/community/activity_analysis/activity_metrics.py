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

import octobot_commons.logging as logging
import octobot_commons.configuration as configuration
import octobot_commons.authentication as authentication
import octobot_commons.constants as common_constants

import octobot_trading.api as trading_api

import octobot.community.activity_analysis.bot_id_resolver as bot_id_resolver
import octobot.community.errors_upload.sentry_tracker as tracker
import octobot.constants as constants
import octobot.enums as enums


class ActivityMetrics:

    def __init__(self, octobot_api):
        self.octobot_api = octobot_api
        self.edited_config: configuration.Configuration = octobot_api.get_edited_config(dict_only=False)
        self.enabled = constants.IS_CLOUD_ENV or self.edited_config.get_metrics_enabled()
        self.logger = logging.get_logger(self.__class__.__name__)
        self.keep_running = True

    @staticmethod
    def initialize_tracker(config: configuration.Configuration) -> None:
        tracker.init_sentry_tracker(metrics_enabled=config.get_metrics_enabled())

    @staticmethod
    def clear_activity_bot_id(config: configuration.Configuration) -> None:
        metrics_section = config.config.setdefault(common_constants.CONFIG_METRICS, {})
        if isinstance(metrics_section, dict):
            metrics_section[common_constants.CONFIG_METRICS_ACTIVITY_BOT_ID] = ""

    def setup_activity_tracking(self, distribution: enums.OctoBotDistribution) -> None:
        if not self.enabled:
            return
        resolution = bot_id_resolver.ensure_activity_bot_id(self.edited_config)
        if tracker.activity_tracking_is_active():
            tracker.update_tracker_bot_id(resolution.bot_id)
            if distribution is enums.OctoBotDistribution.NODE and resolution.was_created:
                tracker.track_usage_event(
                    "node_first_start",
                    distribution="node",
                    version=constants.LONG_VERSION,
                )

    @staticmethod
    def report_child_octobot_first_start() -> None:
        if not tracker.has_tracker_bot_id():
            return
        tracker.track_usage_event("child_octobot_first_start")

    async def start_community_task(self):
        if not self.enabled:
            return
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
