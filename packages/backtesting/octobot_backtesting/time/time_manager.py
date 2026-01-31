#  Drakkar-Software OctoBot-Backtesting
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
import collections
import time

import octobot_commons.logging as logging


class TimeManager:
    DEFAULT_TIMESTAMP_INIT_VALUE = -1
    DEFAULT_FINISH_TIME_DELTA = 1000
    DEFAULT_TIME_INTERVAL = 50

    def __init__(self, config):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.config = config

        self.time_initialized = False

        self.starting_timestamp = self.DEFAULT_TIMESTAMP_INIT_VALUE
        self.finishing_timestamp = self.DEFAULT_TIMESTAMP_INIT_VALUE
        self.current_timestamp = self.DEFAULT_TIMESTAMP_INIT_VALUE
        self.time_interval = self.DEFAULT_TIME_INTERVAL

        self.timestamp_accept_check_callback = None
        self.timestamps_whitelist: set = None
        self._timestamps_whitelist_queue: collections.deque = None

    def initialize(self):
        self._reset_time()
        self.time_initialized = True

    def start(self):
        if self.starting_timestamp == self.DEFAULT_TIMESTAMP_INIT_VALUE:
            self.starting_timestamp = time.time()

        if self.finishing_timestamp == self.DEFAULT_TIMESTAMP_INIT_VALUE:
            self.finishing_timestamp = self.starting_timestamp + self.DEFAULT_FINISH_TIME_DELTA

        self.current_timestamp = self.starting_timestamp

    def _reset_time(self):
        self.set_current_timestamp(0)

    def has_finished(self):
        if self._timestamps_whitelist_queue is not None:
            if len(self._timestamps_whitelist_queue) == 0:
                return True
        return self.current_timestamp >= self.finishing_timestamp

    def next_timestamp(self):
        self.current_timestamp += self.time_interval
        if self._timestamps_whitelist_queue is not None:
            # when timestamps_whitelist is set: fast forward time to only trigger whitelisted timestamps
            while self._should_skip_current_timestamp() and self.current_timestamp <= self.finishing_timestamp:
                self.current_timestamp += self.time_interval

    def _should_skip_current_timestamp(self):
        if self.timestamp_accept_check_callback is not None and self.timestamp_accept_check_callback():
            return False
        return not self._has_current_timestamp_in_whitelist()

    def _has_current_timestamp_in_whitelist(self):
        if self._timestamps_whitelist_queue:
            whitelist_timestamp = self._timestamps_whitelist_queue[0]
            while whitelist_timestamp < self.current_timestamp and self._timestamps_whitelist_queue:
                whitelist_timestamp = self._timestamps_whitelist_queue.popleft()
            return whitelist_timestamp == self.current_timestamp
        return False

    def set_minimum_timestamp(self, minimum_timestamp):
        if self.starting_timestamp == self.DEFAULT_TIMESTAMP_INIT_VALUE or self.starting_timestamp > minimum_timestamp:
            self.starting_timestamp = minimum_timestamp
            self.logger.info(f"Set minimum timestamp to : {minimum_timestamp}")

    def set_maximum_timestamp(self, maximum_timestamp):
        if self.finishing_timestamp == self.DEFAULT_TIMESTAMP_INIT_VALUE or \
                self.finishing_timestamp < maximum_timestamp:
            self.finishing_timestamp = maximum_timestamp
            self.logger.info(f"Set maximum timestamp to : {maximum_timestamp}")

    def set_current_timestamp(self, timestamp):
        self.current_timestamp = timestamp

    def get_total_iteration(self):
        return (self.finishing_timestamp - self.starting_timestamp) / self.time_interval

    def get_remaining_iteration(self):
        return (self.finishing_timestamp - self.current_timestamp) / self.time_interval

    def register_timestamp_whitelist(self, timestamps, check_callback, append_to_whitelist=False):
        self.timestamp_accept_check_callback = check_callback
        if append_to_whitelist and self.timestamps_whitelist:
            self.timestamps_whitelist = sorted(set(self.timestamps_whitelist + timestamps))
        else:
            self.timestamps_whitelist = sorted(set(timestamps))
        self._timestamps_whitelist_queue = collections.deque(self.timestamps_whitelist)
