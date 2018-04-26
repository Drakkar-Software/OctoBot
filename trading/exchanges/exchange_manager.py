import time
from queue import Queue

from tools.asynchronous_server import AsynchronousServer


class ExchangeManager(AsynchronousServer):
    def __init__(self, exchange):
        super().__init__(self.perform_exchange_call)
        self.exchange = exchange
        self.keep_running = True
        self.queue = Queue()
        self.call_id = 0
        self.calls = []
        self.calls_result = []
        self.last_call_time = 0

    def exchange_call(self, exchange_method, **data):
        self.call_id += 1
        self.calls.insert(self.call_id, {
            "exchange_method": exchange_method,
            "data": data
        })
        self.calls_result.insert(self.call_id, Queue())
        return self.add_to_queue(self.call_id)

    def add_to_queue(self, *data):
        self.queue.put(data)
        self.notify_received_data()
        result = self.calls_result[self.call_id].get()
        return result

    def perform_exchange_call(self, call_id):
        # start_time = time.time()

        while True:
            # if time.time() - start_time > timeout:
            #     break

            if time.time() - self.last_call_time < self.exchange.get_rate_limit():
                time.sleep(self.exchange.get_rate_limit()-time.time() - self.last_call_time)
            else:
                result = self.calls[call_id]["exchange_method"](**self.calls[call_id]["data"])
                self.calls_result[call_id].put(result)
                self.last_call_time = time.time()
                break
