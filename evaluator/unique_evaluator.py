from abc import *


class UniqueEvaluator:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.registered_list = {}

    @abstractmethod
    def receive_notification_data(self, data) -> None:
        raise NotImplementedError("receive_notification_data not implemented")

    def notify_registered_evaluators(self, symbol, data):
        for evaluator in self.registered_list[symbol]:
            evaluator.receive_notification_data(data)

    def register_client(self, symbol, client):
        if symbol in self.registered_list:
            self.registered_list[symbol].append(client)
        else:
            self.registered_list[symbol] = [client]