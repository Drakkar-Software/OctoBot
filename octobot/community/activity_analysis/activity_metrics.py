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
import octobot.community.activity_analysis.onboarding_metrics as onboarding_metrics
import octobot.community.activity_analysis.usage_metrics as usage_metrics
import octobot.community.activity_analysis.metrics_connector as metrics_connector
import octobot.community.activity_analysis.metrics_debug as metrics_debug
import octobot.constants as constants
import octobot.enums as enums


class ActivityMetrics:

    def __init__(self, octobot_api):
        self.octobot_api = octobot_api
        self.edited_config: configuration.Configuration = octobot_api.get_edited_config(dict_only=False)
        self.enabled = constants.IS_CLOUD_ENV or self.edited_config.get_metrics_enabled()
        self.logger = logging.get_logger(self.__class__.__name__)
        self.keep_running = True
        self._reconcile_retry_attempts = 0

    @staticmethod
    def initialize_tracker(config: configuration.Configuration) -> None:
        metrics_connector.init_tracker(metrics_enabled=config.get_metrics_enabled())

    @staticmethod
    def clear_activity_bot_id(config: configuration.Configuration) -> None:
        metrics_section = config.config.setdefault(common_constants.CONFIG_METRICS, {})
        if isinstance(metrics_section, dict):
            metrics_section[common_constants.CONFIG_METRICS_ACTIVITY_BOT_ID] = ""

    def setup_activity_tracking(self, distribution: enums.OctoBotDistribution) -> None:
        if not self.enabled:
            return
        resolution = bot_id_resolver.ensure_activity_bot_id(self.edited_config)
        if metrics_connector.activity_tracking_is_active():
            metrics_connector.update_tracker_bot_id(resolution.bot_id)
        if distribution is enums.OctoBotDistribution.NODE and metrics_connector.activity_tracking_is_active():
            usage_metrics.record_node_process_start(
                distribution.value,
                was_new_install=resolution.was_created,
                config=self.edited_config,
            )

    async def start_community_task(self):
        if not self.enabled:
            return
        usage_metrics.ensure_onboarding_state_for_config(self.edited_config)
        try:
            while self.keep_running:
                sleep_seconds = await self._run_reconcile_and_get_loop_sleep_seconds()
                if self.enabled:
                    onboarding_metrics.run_stuck_no_external_interface_background_evaluator(
                        self.edited_config
                    )
                try:
                    await self._update_authenticated_bot()
                except Exception as err:
                    self.logger.debug(f"Exception when handling community data : {err}")
                await asyncio.sleep(sleep_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            self.logger.debug(f"Exception when handling community registration: {err}")

    async def _run_reconcile_and_get_loop_sleep_seconds(self) -> float:
        await usage_metrics.complete_reconcile_automations(self.edited_config)
        pending = onboarding_metrics.get_onboarding_state(
            self.edited_config,
        ).reconcile_automations_pending
        if not pending:
            self._reconcile_retry_attempts = 0
            return common_constants.TIMER_BETWEEN_METRICS_UPTIME_UPDATE
        if self._reconcile_retry_attempts < constants.METRICS_RECONCILE_MAX_RETRY_ATTEMPTS:
            self._reconcile_retry_attempts += 1
            return constants.METRICS_RECONCILE_RETRY_SECONDS
        metrics_debug.log_activity(
            "reconcile_skipped",
            reason="max_retries_exceeded",
            retry_attempts=self._reconcile_retry_attempts,
        )
        return common_constants.TIMER_BETWEEN_METRICS_UPTIME_UPDATE

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
