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

from abc import *
import threading


from tools.logging.logging_util import get_logger
from tools.asyncio_tools import run_coroutine_in_asyncio_loop


# ****** Unique dispatcher side ******
class AbstractDispatcher(threading.Thread):
    __metaclass__ = ABCMeta

    _SLEEPING_TIME_BEFORE_RECONNECT_ATTEMPT_SEC = 10
    DELAY_BETWEEN_STREAMS_QUERIES = 5
    REQUIRED_SERVICE_ERROR_MESSAGE = "Required services are not ready, dispatcher can't start"

    def __init__(self, config, main_async_loop):
        super().__init__()
        self.registered_list = []
        self.config = config
        self.keep_running = True
        self.is_setup_correctly = False
        self.main_async_loop = main_async_loop
        self.logger = get_logger(self.get_name())
        self.service = None

    @classmethod
    def get_name(cls):
        return cls.__name__

    def notify_registered_clients_if_interested(self, notification_description, notification):
        for client in self.registered_list:
            if client.is_interested_by_this_notification(notification_description):
                run_coroutine_in_asyncio_loop(client.receive_notification_data(notification), self.main_async_loop)

    def register_client(self, client):
        self.registered_list.append(client)

    # Override this method if the dispatcher implementation is using a dispatcher handled in the service layer
    # (ie: TelegramDispatcher)
    @staticmethod
    def _get_service_layer_dispatcher():
        return None

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
            self.logger.info("Starting dispatcher ...")
            service_level_dispatcher_if_any = self._get_service_layer_dispatcher()
            if service_level_dispatcher_if_any is not None and self.service is not None:
                self.service.start_dispatcher()
            if self._something_to_watch():
                self._get_data()
                if not self._start_dispatcher():
                    self.logger.warning("Nothing can be monitored even though there is something to watch"
                                        ", dispatcher is going to sleep.")
            else:
                self.logger.info("Nothing to monitor, dispatcher is going to sleep.")

    def get_is_setup_correctly(self):
        return self.is_setup_correctly

    def stop(self):
        self.keep_running = False


# ****** Implementation side ******
class DispatcherAbstractClient:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.dispatcher = None

    @abstractmethod
    async def receive_notification_data(self, data) -> None:
        raise NotImplementedError("receive_notification_data not implemented")

    @staticmethod
    @abstractmethod
    def get_dispatcher_class():
        raise NotImplementedError("get_dispatcher_class not implemented")

    # return true if the given notification is relevant for this client
    @abstractmethod
    def is_interested_by_this_notification(self, notification_description):
        raise NotImplementedError("is_interested_by_this_notification not implemented")

    def set_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher

    def is_client_to_this_dispatcher(self, dispatcher_instance):
        return self.get_dispatcher_class() == dispatcher_instance.__class__
