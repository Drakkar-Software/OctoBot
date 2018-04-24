import logging
import os
import threading
import time

import psutil

from config.cst import MINUTE_TO_SECONDS, CONFIG_DEBUG_OPTION_PERF_REFRESH_TIME_MIN


class PerformanceAnalyser(threading.Thread):
    def __init__(self):
        super().__init__()
        self.keep_running = True
        self.interval = CONFIG_DEBUG_OPTION_PERF_REFRESH_TIME_MIN * MINUTE_TO_SECONDS
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pid = os.getpid()
        self.py = psutil.Process(self.pid)

    def run(self):
        while self.keep_running:
            self.logger.info("CPU : " + str(self._get_cpu()) + "% RAM : " + str(self._get_ram_go()) + " Go")
            time.sleep(self.interval)

    def stop(self):
        self.keep_running = False

    def _get_cpu(self):
        return self.py.cpu_percent()

    def _get_ram_go(self):
        return self.py.memory_info()[0]/2.**30
