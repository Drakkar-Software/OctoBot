import logging
import threading

from flask import request, Flask

from interfaces.web.controllers import bot_blueprint


class WebApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None

    def run(self):
        # Define the WSGI application object
        self.app = Flask(__name__)
        self.app.register_blueprint(bot_blueprint)
        self.app.run(host='localhost', port=5000, debug=False, threaded=True)

    def stop(self):
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            self.logger.warning("Not running with the Werkzeug Server")
        func()
