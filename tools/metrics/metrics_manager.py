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
import copy
import asyncio
import json
import requests
import threading
from concurrent.futures import CancelledError

from config import CONFIG_METRICS_BOT_ID, METRICS_URL, METRICS_ROUTE_GEN_BOT_ID, \
    METRICS_ROUTE_UPTIME, METRICS_ROUTE_REGISTER, TIMER_BEFORE_METRICS_REGISTRATION_SECONDS, \
    TIMER_BETWEEN_METRICS_UPTIME_UPDATE, CONFIG_CATEGORY_NOTIFICATION, CONFIG_NOTIFICATION_TYPE, CONFIG_METRICS, \
    CONFIG_ENABLED_OPTION, MetricsFields
from tools.logging.logging_util import get_logger
from tools.config_manager import ConfigManager
from tools.os_util import get_current_platform, get_octobot_type


class MetricsManager:
    _headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def __init__(self, octobot):
        self.octobot = octobot
        self.edited_config = octobot.edited_config
        self.enabled = ConfigManager.get_metrics_enabled(self.edited_config)
        self.bot_id = self._init_config_bot_id(self.edited_config)
        self.logger = get_logger(self.__class__.__name__)
        self.current_config = None
        self.keep_running = True
        self.session = octobot.get_aiohttp_session()

    def is_enabled(self):
        return self.enabled

    async def start_metrics_task(self):
        if self.enabled:
            try:
                # first ensure this session is not just a configuration test: register after a timer
                await asyncio.sleep(TIMER_BEFORE_METRICS_REGISTRATION_SECONDS)
                await self.register_session()
                while self.keep_running:
                    # send a keepalive at periodic intervals
                    await asyncio.sleep(TIMER_BETWEEN_METRICS_UPTIME_UPDATE)
                    try:
                        await self._update_uptime()
                    except Exception as e:
                        self.logger.debug(f"Exception when handling metrics: {e}")
            except CancelledError:
                pass
            except Exception as e:
                self.logger.debug(f"Exception when handling metrics registration: {e}")

    async def stop_task(self):
        self.keep_running = False
        await self.session.close()

    @staticmethod
    def should_register_bot(config):
        existing_id = MetricsManager._init_config_bot_id(config)
        return not existing_id

    @staticmethod
    def background_get_id_and_register_bot(octobot):
        metrics_manager = MetricsManager(octobot)
        threading.Thread(target=metrics_manager._blocking_get_id_and_register).start()

    def _blocking_get_id_and_register(self):
        try:
            resp = requests.get(f"{METRICS_URL}{METRICS_ROUTE_GEN_BOT_ID}", headers=self._headers)
            text = resp.text
            if resp.status_code != 200:
                self.logger.debug(f"Impossible to get bot id: status code: {resp.status_code}, text: {text}")
            else:
                self.bot_id = json.loads(text)
                self._save_bot_id()
                metrics = self._get_bot_metrics()
                requests.post(f"{METRICS_URL}{METRICS_ROUTE_REGISTER}", json=metrics, headers=self._headers)
        except Exception as e:
            self.logger.debug(f"Error when handling metrics: {e}")

    @staticmethod
    def _init_config_bot_id(config):
        if CONFIG_METRICS in config and config[CONFIG_METRICS] and \
                CONFIG_METRICS_BOT_ID in config[CONFIG_METRICS]:
            return config[CONFIG_METRICS][CONFIG_METRICS_BOT_ID]
        else:
            return None

    async def register_session(self, retry_on_error=True):
        self.current_config = await self._get_current_metrics_config()
        await self._post_metrics(METRICS_ROUTE_REGISTER, self.current_config, retry_on_error)

    async def _update_uptime(self, retry_on_error=True):
        self.current_config[MetricsFields.CURRENT_SESSION.value][MetricsFields.UP_TIME.value] = \
            int(time.time() - self.octobot.start_time)
        await self._post_metrics(METRICS_ROUTE_UPTIME, self.current_config, retry_on_error)

    async def _get_current_metrics_config(self):
        if not self.bot_id:
            await self._init_bot_id()
        if self.bot_id:
            return self._get_bot_metrics()

    def _get_bot_metrics(self):
        return {
            MetricsFields.ID.value: self.bot_id,
            MetricsFields.CURRENT_SESSION.value: {
                MetricsFields.STARTED_AT.value: int(self.octobot.start_time),
                MetricsFields.UP_TIME.value: int(time.time() - self.octobot.start_time),
                MetricsFields.SIMULATOR.value: ConfigManager.get_trader_simulator_enabled(self.edited_config),
                MetricsFields.TRADER.value: ConfigManager.get_trader_enabled(self.edited_config),
                MetricsFields.EVAL_CONFIG.value: self._get_eval_config(),
                MetricsFields.PAIRS.value: self._get_traded_pairs(),
                MetricsFields.EXCHANGES.value: list(self.octobot.get_exchanges_list().keys()),
                MetricsFields.NOTIFICATIONS.value: self._get_notification_types(),
                MetricsFields.TYPE.value: get_octobot_type(),
                MetricsFields.PLATFORM.value: get_current_platform()
            }
        }

    def _get_traded_pairs(self):
        return list(set(evaluator.get_symbol() for evaluator in self.octobot.get_symbol_evaluator_list().values()))

    def _get_notification_types(self):
        has_notifications = CONFIG_CATEGORY_NOTIFICATION in self.edited_config \
                            and CONFIG_NOTIFICATION_TYPE in self.edited_config[CONFIG_CATEGORY_NOTIFICATION]
        return self.edited_config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_NOTIFICATION_TYPE] if has_notifications else []

    def _get_eval_config(self):
        # trading mode
        config_eval = [next(iter(self.octobot.get_exchange_trading_modes().values())).get_name()]

        # strategies
        first_symbol_evaluator = next(iter(self.octobot.get_symbol_evaluator_list().values()))
        first_exchange = next(iter(self.octobot.get_exchanges_list().values()))
        for strategy in first_symbol_evaluator.get_strategies_eval_list(first_exchange):
            config_eval.append(strategy.get_name())

        # evaluators
        first_evaluator = next(iter(self.octobot.get_symbols_tasks_manager().values())).get_evaluator()
        evaluators = copy.copy(first_evaluator.get_social_eval_list())
        evaluators += first_evaluator.get_ta_eval_list()
        evaluators += first_evaluator.get_real_time_eval_list()
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
            self.logger.debug(f"Error when handling metrics: {e}")

    def _save_bot_id(self):
        if CONFIG_METRICS not in self.edited_config or not self.edited_config[CONFIG_METRICS]:
            self.edited_config[CONFIG_METRICS] = {CONFIG_ENABLED_OPTION: True}
        self.edited_config[CONFIG_METRICS][CONFIG_METRICS_BOT_ID] = self.bot_id
        ConfigManager.simple_save_config_update(self.edited_config)

    async def _post_metrics(self, route, bot, retry_on_error):
        try:
            async with self.session.post(f"{METRICS_URL}{route}", json=bot, headers=self._headers) as resp:
                await self._handle_post_error(resp, retry_on_error)
        except Exception as e:
            self.logger.debug(f"Error when handling metrics: {e}")

    async def _handle_post_error(self, resp, retry_on_error):
        if resp.status != 200:
            if resp.status == 404:
                # did not found bot with id in config: generate new id and register new bot
                if retry_on_error:
                    await self._init_bot_id()
                    await self.register_session(retry_on_error=False)
            else:
                self.logger.debug(f"Impossible to send metrics: status code: {resp.status}, text: {await resp.text()}")
