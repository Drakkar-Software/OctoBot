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

    def run(self):
        # wait bot is ready
        while get_bot() is None or not get_bot().is_ready():
            sleep(0.1)

        # Define the WSGI application object
        self.app = server_instance

        load_routes()

        self.app.run(host=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP],
                     port=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT],
                     debug=False,
                     threaded=True)

    def stop(self):
        # func = request.environ.get('werkzeug.server.shutdown')
        # if func is None:
        #     raise RuntimeError('Not running with the Werkzeug Server')
        # func()
        pass
