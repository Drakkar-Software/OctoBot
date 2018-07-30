import socket

from config.cst import CONFIG_WEB, CONFIG_CATEGORY_SERVICES, CONFIG_ENABLED_OPTION, CONFIG_SERVICE_INSTANCE, \
    CONFIG_WEB_IP, CONFIG_WEB_PORT, DEFAULT_SERVER_IP, DEFAULT_SERVER_PORT
from interfaces.web.web_app import WebApp
from services import AbstractService


class WebService(AbstractService):
    REQUIRED_CONFIG = {"port": 5000}

    BACKTESTING_ENABLED = True

    def __init__(self):
        super().__init__()
        self.web_app = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_WEB in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_WEB in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION]

    def get_endpoint(self) -> None:
        return self.web_app

    def get_type(self) -> None:
        return CONFIG_WEB

    def prepare(self) -> None:
        self.web_app = WebApp(self.config)
        self.web_app.start()

    @staticmethod
    def get_should_warn():
        return False

    def stop(self):
        if self.web_app:
            self.web_app.stop()

    @staticmethod
    def enable(config, is_enabled):
        if CONFIG_CATEGORY_SERVICES not in config:
            config[CONFIG_CATEGORY_SERVICES] = {}
        if CONFIG_WEB not in config[CONFIG_CATEGORY_SERVICES]:
            config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB] = {}
            config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP] = DEFAULT_SERVER_IP
            config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT] = DEFAULT_SERVER_PORT
        else:
            if CONFIG_WEB_IP not in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]:
                config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP] = DEFAULT_SERVER_IP
            if CONFIG_WEB_PORT not in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]:
                config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT] = DEFAULT_SERVER_PORT

        config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION] = is_enabled

    def _get_web_server_url(self):
        return "{0}:{1}"\
            .format(socket.gethostbyname(socket.gethostname()),
                    self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT])

    def get_successful_startup_message(self):
        return "Interface successfully initialized and accessible at: http://{0}.".format(self._get_web_server_url())
