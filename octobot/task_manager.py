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
import platform
import threading
from asyncio import CancelledError

from config import FORCE_ASYNCIO_DEBUG_OPTION
from tools.asyncio_tools import get_gather_wrapper, run_coroutine_in_asyncio_loop
from octobot_commons.logging.logging_util import get_logger

try:
    import uvloop
except ImportError:
    get_logger().debug("uvloop is not installed")


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
        self.tools_task_group = None
        self.current_loop_thread = None

    def init_async_loop(self):
        self.async_loop = asyncio.get_running_loop()
        self.__init_uv_loop()

    def __init_uv_loop(self):
        if platform == "linux" or platform == "linux2":  # TODO centralize os detection
            uvloop.install()
        elif platform == "darwin":
            uvloop.install()
        elif platform == "win32":
            pass

    async def start_tools_tasks(self, run_in_new_thread=False):
        task_list = []
        # if self.octobot.initializer.performance_analyser:
        #     task_list.append(self.octobot.initializer.performance_analyser.start_monitoring())

        # if self.octobot.metrics_handler:
        #     task_list.append(self.octobot.metrics_handler.start_metrics_task())

        self.octobot.async_loop = self.async_loop
        self.ready = True
        self.tools_task_group = asyncio.gather(*task_list)

        # if run_in_new_thread:
        #     self._create_new_asyncio_main_loop()
        # else:
        #     self.current_loop_thread = threading.current_thread()
        #     await self.tools_task_group

    async def join_tasks(self):
        try:
            await asyncio.gather(*asyncio.all_tasks(asyncio.get_event_loop()))
        except CancelledError:
            self.logger.error("CancelledError raised")

    async def stop_tasks(self):
        stop_coroutines = []
        # Notify stopping
        # if self.octobot.config[CONFIG_NOTIFICATION_INSTANCE].enabled(CONFIG_NOTIFICATION_GLOBAL_INFO):
        #     # To be improved with a full async implementation
        #     # To be done : "asyncio.run" --> replaced by a simple await
        #     # PR discussion : https://github.com/Drakkar-Software/OctoBot/pull/563#discussion_r248088266
        #     stop_coroutines.append(self.octobot.config[CONFIG_NOTIFICATION_INSTANCE]
        #                            .notify_with_all(NOTIFICATION_STOPPING_MESSAGE))

        self.logger.info("Stopping threads ...")

        if self.tools_task_group:
            self.async_loop.call_soon_threadsafe(self.tools_task_group.cancel)

        # close metrics session
        stop_coroutines.append(self.octobot.metrics_handler.stop_task())

        for task in asyncio.all_tasks():
            task.cancel()

        self.async_loop.close()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.run(get_gather_wrapper(stop_coroutines))

        self.logger.info("Threads stopped.")

    def __create_new_asyncio_main_loop(self):
        self.async_loop = asyncio.new_event_loop()
        self.async_loop.set_debug(FORCE_ASYNCIO_DEBUG_OPTION)
        asyncio.set_event_loop(self.async_loop)
        self.current_loop_thread = threading.Thread(target=self.async_loop.run_forever)
        self.current_loop_thread.start()

    def run_in_main_asyncio_loop(self, coroutine):
        # restart a new loop if necessary (for backtesting analysis)
        # if backtesting_enabled(self.octobot.config) and self.async_loop.is_closed(): TODO
        #     self.logger.debug("Main loop is closed, starting a new main loop.")
        #     self._create_new_asyncio_main_loop()

        return run_coroutine_in_asyncio_loop(coroutine, self.async_loop)
