import threading
from abc import *

from tools.asynchronous_server import AsynchronousServer


# ****** Unique dispatcher side ******
from tools.logging.logging_util import get_logger


class AbstractDispatcher(threading.Thread):
    __metaclass__ = ABCMeta

    _SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC = 10

    def __init__(self, config):
        super().__init__()
        self.registered_list = []
        self.config = config
        self.keep_running = True
        self.is_setup_correctly = False
        self.logger = get_logger(self.__class__.__name__)

    def notify_registered_clients_if_interested(self, notification_description, notification):
        for client in self.registered_list:
            if client.is_interested_by_this_notification(notification_description):
                client.add_to_queue(notification)

    def register_client(self, client):
        self.registered_list.append(client)

    @abstractmethod
    def _start_dispatcher(self):
        raise NotImplementedError("start_dispatcher not implemented")

    @abstractmethod
    def _something_to_watch(self):
        raise NotImplementedError("_something_to_watch not implemented")

    @abstractmethod
    def _get_data(self):
        raise NotImplementedError("_get_data not implemented")

    def run(self):
        if self.is_setup_correctly:
            if self._something_to_watch():
                self._get_data()
                self._start_dispatcher()
                self.logger.warning("Nothing can be monitored even though there is something to watch"
                                    ", dispatcher is going to sleep.")
            else:
                self.logger.info("Nothing to monitor, dispatcher is going to sleep.")

    def get_is_setup_correctly(self):
        return self.is_setup_correctly

    def stop(self):
        self.keep_running = False


# ****** Implementation side ******
class DispatcherAbstractClient(AsynchronousServer):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__(self.receive_notification_data)
        self.dispatcher = None

    @abstractmethod
    def receive_notification_data(self, data) -> None:
        raise NotImplementedError("receive_notification_data not implemented")

    @staticmethod
    @abstractmethod
    def get_dispatcher_class():
        raise NotImplementedError("get_dispatcher_class not implemented")

    def set_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher

    # return true if the given notification is relevant for this client
    @abstractmethod
    def is_interested_by_this_notification(self, notification_description):
        raise NotImplementedError("is_interested_by_this_notification not implemented")

    def is_client_to_this_dispatcher(self, dispatcher_instance):
        return self.get_dispatcher_class() == dispatcher_instance.__class__
