from config.cst import CONFIG_WEB, CONFIG_CATEGORY_SERVICES, CONFIG_ENABLED_OPTION, CONFIG_SERVICE_INSTANCE
from interfaces.web.app import WebApp
from services import AbstractService


class WebService(AbstractService):
    def __init__(self):
        super().__init__()
        self.web_app = None

    @staticmethod
    def is_setup_correctly(config):
        if CONFIG_WEB in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]:
            return True
        else:
            return False

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
    def enable(config):
        if CONFIG_CATEGORY_SERVICES not in config:
            config[CONFIG_CATEGORY_SERVICES] = {}
        if CONFIG_WEB not in config[CONFIG_CATEGORY_SERVICES]:
            config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB] = {}
        config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION] = True
