import logging
import threading

from flask import request, Flask

from config.cst import CONFIG_ENABLED_OPTION


class WebApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None

    def enabled(self):
        if "interfaces" in self.config \
                and "web" in self.config["interfaces"] \
                and self.config["interfaces"]["web"][CONFIG_ENABLED_OPTION]:
            return True
        else:
            return False

    def run(self):
        self.app = Flask(__name__)
        self.app.use_reloader = False
        self.app.run(host='localhost', port=5000, debug=False, threaded=True)

    def stop(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            self.logger.warning("Not running with the Werkzeug Server")
        func()

