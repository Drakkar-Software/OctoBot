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

from tools.logging.logging_util import get_logger
import threading
from queue import Queue

"""
The asynchronous server tool class is used as a inherited class to use a FIFO implementation in an Octobot class
"""


class AsynchronousServer:

    def __init__(self, callback_method):
        self.is_computing = False
        self.queue = Queue()
        self.callback_method = callback_method
        self.logger = get_logger(self.__class__.__name__)

    def has_something_to_do(self):
        return not self.queue.empty() or self.is_computing

    def add_to_queue(self, *data):
        self.queue.put(data)
        self.notify_received_data()

    def notify_received_data(self):
        if not self.is_computing:
            self.is_computing = True
            threading.Thread(target=self.process_queue).start()

    def process_queue(self):
        try:
            while not self.queue.empty():
                self.callback_method(*self.queue.get())
        except Exception as e:
            self.logger.error("Error while processing queue")
            self.logger.exception(e)
        finally:
            self.is_computing = False
