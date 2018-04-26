import time
from queue import Queue

from tools.asynchronous_server import AsynchronousServer


class ExchangeManager(AsynchronousServer):
    def __init__(self, exchange):
        super().__init__(self.perform_exchange_call)
        self.exchange = exchange
        self.keep_running = True
        self.call_id = 0
        self.calls = []
        self.last_call_time = 0

    def exchange_call(self, exchange_method, **data):
        self.call_id += 1
        self.calls.insert(self.call_id, {
            "exchange_method": exchange_method,
            "data": data,
            "result": Queue()
        })
        return self.add_to_queue(self.call_id)

    def add_to_queue(self, *data):
        self.queue.put(data)
        self.notify_received_data()
        result = self.calls[data]["result"].get()
        self.calls.remove(data)
        return result

    def perform_exchange_call(self, call_id):

        while self.keep_running:
            # if time.time() - start_time > timeout:
            #     break
            
            now_time = time.time()
            if now_time - self.last_call_time < self.exchange.get_rate_limit():
                time.sleep(self.exchange.get_rate_limit() - now_time - self.last_call_time)
            else:
                call_data = self.calls[call_id]
                result = call_data["exchange_method"](**call_data["data"])
                call_data["result"].put(result)
                self.last_call_time = time.time()
                break
                  
    def stop(self):
        self.keep_running = False
