import logging
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
        self.logger = logging.getLogger(self.__class__.__name__)

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
