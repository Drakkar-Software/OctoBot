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
from werkzeug.serving import make_server

from tools.logging.logging_util import get_logger
import threading
from time import sleep

from config import CONFIG_WEB, CONFIG_CATEGORY_SERVICES, CONFIG_WEB_IP, CONFIG_WEB_PORT
from interfaces import get_bot
from interfaces.web import server_instance
from interfaces.web.controllers import load_routes


class WebApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

        self.app = None
        self.srv = None
        self.ctx = None

    def prepare_server(self):
        try:
            self.srv = make_server(host=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP],
                                   port=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT],
                                   threaded=True,
                                   app=server_instance)
            self.ctx = server_instance.app_context()
            self.ctx.push()
        except OSError as e:
            self.srv = None
            self.logger.exception(f"Fail to start web interface : {e}")

    def run(self):
        # wait bot is ready
        while get_bot() is None or not get_bot().is_ready():
            sleep(0.1)

        # Define the WSGI server object
        self.prepare_server()

        load_routes()

        if self.srv:
            self.srv.serve_forever()

    def prepare_stop(self):
        self.srv.server_close()

    def stop(self):
        self.prepare_stop()
        self.srv.shutdown()
