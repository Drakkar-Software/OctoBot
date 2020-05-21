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
import time
import asyncio
import json
import requests
import threading
from concurrent.futures import CancelledError

from octobot_commons.constants import CONFIG_METRICS_BOT_ID, METRICS_URL, METRICS_ROUTE_GEN_BOT_ID, \
    METRICS_ROUTE_UPTIME, METRICS_ROUTE_REGISTER, TIMER_BEFORE_METRICS_REGISTRATION_SECONDS, \
    TIMER_BETWEEN_METRICS_UPTIME_UPDATE, CONFIG_METRICS, \
    CONFIG_ENABLED_OPTION
from octobot_evaluators.api.evaluators import get_evaluator_classes_from_type
from octobot_evaluators.enums import EvaluatorMatrixTypes
from octobot_trading.api.exchange import get_trading_pairs, get_exchange_names, get_exchange_managers_from_exchange_ids
from octobot.community.community_fields import CommunityFields
from octobot_services.constants import CONFIG_CATEGORY_NOTIFICATION, CONFIG_NOTIFICATION_TYPE
from octobot_commons.logging.logging_util import get_logger
from octobot_commons.config_manager import get_metrics_enabled, simple_save_config_update
from octobot_commons.os_util import get_current_platform, get_octobot_type

from octobot_trading.api.profitability import get_reference_market, get_current_portfolio_value, \
    get_origin_portfolio_value, get_profitability_stats
from octobot_trading.api.trader import is_trader_enabled_in_config, is_trader_simulator_enabled_in_config


class CommunityManager:
    _headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def __init__(self, octobot_api):
        self.octobot_api = octobot_api
        self.edited_config = octobot_api.get_edited_config()
        self.enabled = get_metrics_enabled(self.edited_config)
        self.bot_id = self._init_config_bot_id(self.edited_config)
        self.reference_market = get_reference_market(self.edited_config)
        self.logger = get_logger(self.__class__.__name__)
        self.current_config = None
        self.keep_running = True
        self.session = octobot_api.get_aiohttp_session()
        self.has_real_trader = is_trader_enabled_in_config(self.edited_config)
        self.has_simulator = is_trader_simulator_enabled_in_config(self.edited_config)
        self.exchange_managers = get_exchange_managers_from_exchange_ids(
            self.octobot_api.get_exchange_manager_ids())

    async def start_community_task(self):
        if self.enabled:
            try:
                # first ensure this session is not just a configuration test: register after a timer
                await asyncio.sleep(TIMER_BEFORE_METRICS_REGISTRATION_SECONDS)
                await self.register_session()
                while self.keep_running:
                    # send a keepalive at periodic intervals
                    await asyncio.sleep(TIMER_BETWEEN_METRICS_UPTIME_UPDATE)
                    try:
                        await self._update_uptime_and_profitability()
                    except Exception as e:
                        self.logger.debug(f"Exception when handling community data : {e}")
            except CancelledError:
                pass
            except Exception as e:
                self.logger.debug(f"Exception when handling community registration: {e}")

    async def stop_task(self):
        self.keep_running = False
        await self.session.close()

    @staticmethod
    def should_register_bot(config):
        existing_id = CommunityManager._init_config_bot_id(config)
        return not existing_id

    @staticmethod
    def background_get_id_and_register_bot(octobot_api):
        community_manager = CommunityManager(octobot_api)
        threading.Thread(target=community_manager._blocking_get_id_and_register).start()

    def _blocking_get_id_and_register(self):
        try:
            resp = requests.get(f"{METRICS_URL}{METRICS_ROUTE_GEN_BOT_ID}", headers=self._headers)
            text = resp.text
            if resp.status_code != 200:
                self.logger.debug(f"Impossible to get bot id: status code: {resp.status_code}, text: {text}")
            else:
                self.bot_id = json.loads(text)
                self._save_bot_id()
                community = self._get_bot_community()
                requests.post(f"{METRICS_URL}{METRICS_ROUTE_REGISTER}", json=community, headers=self._headers)
        except Exception as e:
            self.logger.debug(f"Error when handling community: {e}")

    @staticmethod
    def _init_config_bot_id(config):
        if CONFIG_METRICS in config and config[CONFIG_METRICS] and \
                CONFIG_METRICS_BOT_ID in config[CONFIG_METRICS]:
            return config[CONFIG_METRICS][CONFIG_METRICS_BOT_ID]
        else:
            return None

    async def register_session(self, retry_on_error=True):
        self.current_config = await self._get_current_community_config()
        await self._post_community_data(METRICS_ROUTE_REGISTER, self.current_config, retry_on_error)

    async def _update_uptime_and_profitability(self, retry_on_error=True):
        self.current_config[CommunityFields.CURRENT_SESSION.value][CommunityFields.UP_TIME.value] = \
            int(time.time() - self.octobot_api.get_start_time())
        self.current_config[CommunityFields.CURRENT_SESSION.value][CommunityFields.PROFITABILITY.value] = \
            self._get_profitability()
        await self._post_community_data(METRICS_ROUTE_UPTIME, self.current_config, retry_on_error)

    async def _get_current_community_config(self):
        if not self.bot_id:
            await self._init_bot_id()
        if self.bot_id:
            return self._get_bot_community()

    def _get_bot_community(self):
        return {
            CommunityFields.ID.value: self.bot_id,
            CommunityFields.CURRENT_SESSION.value: {
                CommunityFields.STARTED_AT.value: int(self.octobot_api.get_start_time()),
                CommunityFields.UP_TIME.value: int(time.time() - self.octobot_api.get_start_time()),
                CommunityFields.SIMULATOR.value: self.has_simulator,
                CommunityFields.TRADER.value: self.has_real_trader,
                CommunityFields.EVAL_CONFIG.value: self._get_eval_config(),
                CommunityFields.PAIRS.value: self._get_traded_pairs(),
                CommunityFields.EXCHANGES.value: list(get_exchange_names()),
                CommunityFields.NOTIFICATIONS.value: self._get_notification_types(),
                CommunityFields.TYPE.value: get_octobot_type(),
                CommunityFields.PLATFORM.value: get_current_platform(),
                CommunityFields.REFERENCE_MARKET.value: self.reference_market,
                CommunityFields.PORTFOLIO_VALUE.value: self._get_real_portfolio_value(),
                CommunityFields.PROFITABILITY.value: self._get_profitability()
            }
        }

    def _get_profitability(self):
        total_origin_values = 0
        total_profitability = 0

        for exchange_manager in self.exchange_managers:
            profitability, _, _, _, _ = get_profitability_stats(exchange_manager)
            total_profitability += profitability
            total_origin_values += get_current_portfolio_value(exchange_manager)

        return total_profitability * 100 / total_origin_values if total_origin_values > 0 else 0

    def _get_real_portfolio_value(self):
        if self.has_real_trader:
            total_value = 0
            for exchange_manager in self.exchange_managers:
                current_value = get_current_portfolio_value(exchange_manager)
                # current_value might be 0 if no trades have been made / canceled => use origin value
                if current_value == 0:
                    current_value = get_origin_portfolio_value(exchange_manager)
                total_value += current_value
            return total_value
        else:
            return 0

    def _get_traded_pairs(self):
        pairs = set()
        for exchange_manager in self.exchange_managers:
            pairs = pairs.union(get_trading_pairs(exchange_manager))
        return list(pairs)

    def _get_notification_types(self):
        has_notifications = CONFIG_CATEGORY_NOTIFICATION in self.edited_config \
                            and CONFIG_NOTIFICATION_TYPE in self.edited_config[CONFIG_CATEGORY_NOTIFICATION]
        return self.edited_config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_NOTIFICATION_TYPE] if has_notifications else []

    def _get_eval_config(self):
        tentacle_setup_config = self.octobot_api.get_tentacles_setup_config()
        # trading mode
        config_eval = [self.octobot_api.get_trading_mode().get_name()]

        # strategies
        for strategy in get_evaluator_classes_from_type(EvaluatorMatrixTypes.STRATEGIES.value,
                                                        tentacle_setup_config):
            config_eval.append(strategy.get_name())

        # evaluators
        evaluators = get_evaluator_classes_from_type(EvaluatorMatrixTypes.TA.value,
                                                     tentacle_setup_config)
        evaluators += get_evaluator_classes_from_type(EvaluatorMatrixTypes.SOCIAL.value,
                                                      tentacle_setup_config)
        evaluators += get_evaluator_classes_from_type(EvaluatorMatrixTypes.REAL_TIME.value,
                                                      tentacle_setup_config)
        for evaluator in evaluators:
            config_eval.append(evaluator.get_name())
        return config_eval

    async def _init_bot_id(self):
        try:
            async with self.session.get(f"{METRICS_URL}{METRICS_ROUTE_GEN_BOT_ID}", headers=self._headers) as resp:
                text = await resp.text()
                if resp.status != 200:
                    self.logger.debug(f"Impossible to get bot id: status code: {resp.status}, text: {text}")
                else:
                    self.bot_id = json.loads(text)
                    self._save_bot_id()
        except Exception as e:
            self.logger.debug(f"Error when handling community data : {e}")

    def _save_bot_id(self):
        if CONFIG_METRICS not in self.edited_config or not self.edited_config[CONFIG_METRICS]:
            self.edited_config[CONFIG_METRICS] = {CONFIG_ENABLED_OPTION: True}
        self.edited_config[CONFIG_METRICS][CONFIG_METRICS_BOT_ID] = self.bot_id
        simple_save_config_update(self.edited_config)

    async def _post_community_data(self, route, bot, retry_on_error):
        try:
            async with self.session.post(f"{METRICS_URL}{route}", json=bot, headers=self._headers) as resp:
                await self._handle_post_error(resp, retry_on_error)
        except Exception as e:
            self.logger.debug(f"Error when handling community data : {e}")

    async def _handle_post_error(self, resp, retry_on_error):
        if resp.status != 200:
            if resp.status == 404:
                # did not found bot with id in config: generate new id and register new bot
                if retry_on_error:
                    await self._init_bot_id()
                    await self.register_session(retry_on_error=False)
            else:
                self.logger.debug(f"Impossible to send community data : "
                                  f"status code: {resp.status}, "
                                  f"text: {await resp.text()}")
