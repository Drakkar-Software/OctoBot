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
import os
import psutil

from tools.logging.logging_util import get_logger

from config import MINUTE_TO_SECONDS, CONFIG_DEBUG_OPTION_PERF_REFRESH_TIME_MIN


class PerformanceAnalyser:
    def __init__(self):
        super().__init__()
        self.keep_running = True
        self.interval = CONFIG_DEBUG_OPTION_PERF_REFRESH_TIME_MIN * MINUTE_TO_SECONDS
        self.logger = get_logger(self.__class__.__name__)
        self.pid = os.getpid()
        self.py = psutil.Process(self.pid)

    async def start_monitoring(self):
        while self.keep_running:
            self.logger.info(f"CPU : {self._get_cpu()}% RAM : {self._get_ram_go()} Go")
            await asyncio.sleep(self.interval)

    def stop(self):
        self.keep_running = False

    def _get_cpu(self):
        return self.py.cpu_percent()

    def _get_ram_go(self):
        return self.py.memory_info()[0]/2.**30
