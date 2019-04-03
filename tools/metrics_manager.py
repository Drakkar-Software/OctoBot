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


import requests
import time
import copy
import asyncio

from config import CONFIG_ENABLE_METRICS, CONFIG_METRICS_BOT_ID, METRICS_URL, METRICS_ROUTE_GEN_BOT_ID, \
    METRICS_ROUTE_UPTIME, METRICS_ROUTE_REGISTER, TIMER_BEFORE_METRICS_REGISTRATION_SECONDS, \
    TIMER_BETWEEN_METRICS_UPTIME_UPDATE
from tools.logging.logging_util import get_logger
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator


class MetricsManager:
    _headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def __init__(self, octobot):
        self.octobot = octobot
        self.config = octobot.get_config()
        self.enabled = (CONFIG_ENABLE_METRICS in self.config and self.config[CONFIG_ENABLE_METRICS]) \
            or CONFIG_ENABLE_METRICS not in self.config
        self.bot_id = self.config[CONFIG_METRICS_BOT_ID] \
            if CONFIG_METRICS_BOT_ID in self.config and self.config[CONFIG_METRICS_BOT_ID] \
            else None
        self.logger = get_logger(self.__class__.__name__)
        self.current_config = None
        self.keep_running = True

    def is_enabled(self):
        return self.enabled

    async def start_metrics_task(self):
        if self.enabled:
            # first ensure this session is not just a configuration test: register after a timer
            await asyncio.sleep(TIMER_BEFORE_METRICS_REGISTRATION_SECONDS)
            self._register_session()
            while self.keep_running:
                # send a keepalive at periodic intervals
                await asyncio.sleep(TIMER_BETWEEN_METRICS_UPTIME_UPDATE)
                try:
                    self._update_uptime()
                except Exception as e:
                    self.logger.debug(f"Exception when handling metrics: {e}")

    def _register_session(self):
        self.current_config = self._get_current_metrics_config()
        self._post_metrics(METRICS_ROUTE_REGISTER, self.current_config)

    def _update_uptime(self):
        self.current_config["currentSession"]["uptime"] = int(time.time() - self.octobot.start_time)
        self._post_metrics(METRICS_ROUTE_UPTIME, self.current_config)

    def _get_current_metrics_config(self):
        if not self.bot_id:
            self._init_bot_id()
        if self.bot_id:

            return {
                "_id": self.bot_id,
                "currentSession": {
                    "startedat": int(self.octobot.start_time),
                    "uptime": int(time.time() - self.octobot.start_time),
                    "simulator": TraderSimulator.enabled(self.config),
                    "trader": Trader.enabled(self.config),
                    "evalconfig": self._get_eval_config(),
                    "exchanges": list(self.octobot.get_exchanges_list().keys())
                }
            }

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

    def _init_bot_id(self):
        answer = requests.get(f"{METRICS_URL}{METRICS_ROUTE_GEN_BOT_ID}", headers=self._headers)
        if answer.status_code != 200:
            self.logger.debug(f"Impossible to get bot id: status code: {answer.status_code}, text: {answer.text}")
        else:
            self.bot_id = answer.text.strip()

    def _post_metrics(self, route, bot):
        answer = requests.post(f"{METRICS_URL}{route}", json=bot, headers=self._headers)
        if answer.status_code != 200:
            self.logger.debug(f"Impossible to send metrics: status code: {answer.status_code}, text: {answer.text}")
