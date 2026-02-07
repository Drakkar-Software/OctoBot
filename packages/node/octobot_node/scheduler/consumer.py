#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

import logging
import threading

from octobot_node.config import settings

from octobot_node.scheduler.scheduler import Scheduler
from huey.constants import WORKER_THREAD

class SchedulerConsumer:
    def __init__(self, scheduler: Scheduler):
        self.scheduler: Scheduler = scheduler
        self.consumer = None
        self.thread = None
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        self.workers: int | None = None
    
    def start(self):
        with self.lock:
            if self.thread is None or not self.thread.is_alive():
                self.start_thread()
                self.logger.info("Scheduler consumer thread started automatically on import")
    
    def _run(self):
        if not self.consumer:
            self.logger.error("Consumer not initialized. Cannot start consumer thread.")
            return
        self.logger.info("Starting consumer...")
        try:
            self.consumer.run()
        except ValueError as e:
            # Ignore `ValueError: signal only works in main thread of the main interpreter``
            self.logger.debug(f"ValueError ignored when starting consumer: {e}")

    def start_thread(self) -> None:
        if settings.SCHEDULER_WORKERS <= 0:
            self.logger.info("Consumers are disabled.")
            self.workers = None
            return
        self.logger.info(f"Starting {settings.SCHEDULER_WORKERS} scheduler consumer")
        self.workers = settings.SCHEDULER_WORKERS
        config_values = {
            "worker_type": WORKER_THREAD,
            "workers": self.workers,
        }
        self.consumer = self.scheduler.INSTANCE.create_consumer(**config_values)
        self.logger.info(
            f"Scheduler consumer started with {self.workers} workers (worker_type=thread)",
            self.workers
        )
        self.thread = threading.Thread(
            target=self._run,
            args=(),
            name="scheduler-consumer",
            daemon=True,
        )
        self.thread.start()
        self.logger.info("Scheduler consumer running in thread")

    def is_started(self) -> bool:
        with self.lock:
            return self.thread is not None

    def is_running(self) -> bool:
        with self.lock:
            return self.thread is not None and self.thread.is_alive()

    def stop(self) -> None:
        with self.lock:
            if not self.consumer:
                return

            self.consumer.stop(graceful=True)
            if self.thread:
                self.thread.join(timeout=5)

            self.logger.info("Scheduler consumer stopped")
            self.consumer = None
            self.thread = None
            self.workers = None
