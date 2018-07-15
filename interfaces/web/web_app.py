import logging
import threading
from time import sleep

from config.cst import CONFIG_WEB, CONFIG_CATEGORY_SERVICES, CONFIG_WEB_IP, CONFIG_WEB_PORT
from interfaces import get_bot
from interfaces.web import app_instance, load_callbacks, load_routes, load_advanced_routes
from interfaces.web.util.dash_dashboard import create_dashboard


class WebApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None

    def run(self):

        # wait bot is ready
        while get_bot() is None or not get_bot().is_ready():
            sleep(0.1)

        # Define the WSGI application object
        self.app = app_instance

        create_dashboard(self)

        load_callbacks()
        load_routes()
        load_advanced_routes()
        self.app.run_server(host=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP],
                            port=self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT],
                            debug=False,
                            threaded=True)

    def stop(self):
        # func = request.environ.get('werkzeug.server.shutdown')
        # if func is None:
        #     raise RuntimeError('Not running with the Werkzeug Server')
        # func()
        pass
