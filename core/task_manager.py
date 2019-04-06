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
import asyncio
import threading

from backtesting import backtesting_enabled
from config import CONFIG_NOTIFICATION_INSTANCE, CONFIG_NOTIFICATION_GLOBAL_INFO, FORCE_ASYNCIO_DEBUG_OPTION, \
    NOTIFICATION_STOPPING_MESSAGE
from services import ServiceCreator
from tools.asyncio_tools import get_gather_wrapper, run_coroutine_in_asyncio_loop
from tools.logging.logging_util import get_logger


class TaskManager:
    """TaskManager class:
        - Create, manage and stop octobot tasks
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.async_loop = None
        self.ready = False
        self.watcher = None
        self.main_task_group = None
        self.current_loop_thread = None

    def init_async_loop(self):
        self.async_loop = asyncio.get_running_loop()

    async def start_tasks(self, run_in_new_thread=False):
        task_list = []
        if self.octobot.initializer.performance_analyser:
            task_list.append(self.octobot.initializer.performance_analyser.start_monitoring())

        for crypto_currency_evaluator in self.octobot.get_crypto_currency_evaluator_list().values():
            task_list.append(crypto_currency_evaluator.get_social_evaluator_refresh_task())

        for trader in self.octobot.get_exchange_traders().values():
            if trader.is_enabled():
                await trader.launch()
                task_list.append(trader.start_order_manager())

        for trader_simulator in self.octobot.get_exchange_trader_simulators().values():
            if trader_simulator.is_enabled():
                await trader_simulator.launch()
                task_list.append(trader_simulator.start_order_manager())

        for updater in self.octobot.get_global_updaters_by_exchange().values():
            if self.watcher is not None:
                updater.set_watcher(self.watcher)
            task_list.append(updater.start_update_loop())

        for real_time_eval in self.octobot.evaluator_factory.real_time_eval_tasks:
            task_list.append(real_time_eval.start_task())

        for social_eval in self.octobot.evaluator_factory.social_eval_tasks:
            task_list.append(social_eval.start_task())

        if self.octobot.metrics_handler:
            task_list.append(self.octobot.metrics_handler.start_metrics_task())

        for thread in self.octobot.get_dispatchers_list():
            thread.start()

        self.logger.info("Evaluation tasks started...")
        self.octobot.async_loop = self.async_loop
        self.ready = True
        self.main_task_group = asyncio.gather(*task_list)

        if run_in_new_thread:
            self._create_new_asyncio_main_loop()
        else:
            self.current_loop_thread = threading.current_thread()
            await self.main_task_group

    def join_threads(self):
        for thread in self.octobot.get_dispatchers_list():
            thread.join()

    def stop_threads(self):
        stop_coroutines = []
        # Notify stopping
        if self.octobot.get_config()[CONFIG_NOTIFICATION_INSTANCE].enabled(CONFIG_NOTIFICATION_GLOBAL_INFO):
            # To be improved with a full async implementation
            # To be done : "asyncio.run" --> replaced by a simple await
            # PR discussion : https://github.com/Drakkar-Software/OctoBot/pull/563#discussion_r248088266
            stop_coroutines.append(self.octobot.get_config()[CONFIG_NOTIFICATION_INSTANCE]
                                   .notify_with_all(NOTIFICATION_STOPPING_MESSAGE))

        self.logger.info("Stopping threads ...")

        if self.main_task_group:
            self.async_loop.call_soon_threadsafe(self.main_task_group.cancel)

        for thread in self.octobot.get_dispatchers_list():
            thread.stop()

        # stop services
        for service_instance in ServiceCreator.get_service_instances(self.octobot.get_config()):
            try:
                service_instance.stop()
            except Exception as e:
                raise e

        # close metrics session
        stop_coroutines.append(self.octobot.metrics_handler.stop_task())

        # stop exchanges threads
        for exchange in self.octobot.exchange_factory.exchanges_list.values():
            stop_coroutines.append(exchange.stop())

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.run(get_gather_wrapper(stop_coroutines))

        self.logger.info("Threads stopped.")

    def _create_new_asyncio_main_loop(self):
        self.async_loop = asyncio.new_event_loop()
        self.async_loop.set_debug(FORCE_ASYNCIO_DEBUG_OPTION)
        asyncio.set_event_loop(self.async_loop)
        self.current_loop_thread = threading.Thread(target=self.async_loop.run_forever)
        self.current_loop_thread.start()

    def run_in_main_asyncio_loop(self, coroutine):
        # restart a new loop if necessary (for backtesting analysis)
        if backtesting_enabled(self.octobot.get_config()) and self.async_loop.is_closed():
            self.logger.debug("Main loop is closed, starting a new main loop.")
            self._create_new_asyncio_main_loop()

        return run_coroutine_in_asyncio_loop(coroutine, self.async_loop)
