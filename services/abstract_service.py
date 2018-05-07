from abc import *


class AbstractService:
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.logger = None
        self.config = None
        self.enabled = True

    @classmethod
    def get_name(cls):
        return cls.__name__

    # Returns true if all the service has an instance in config
    @staticmethod
    @abstractmethod
    def is_setup_correctly(config):
        raise NotImplementedError("is_setup_correctly not implemented")

    # Used to provide a new logger for this particular indicator
    def set_logger(self, logger):
        self.logger = logger

    # Used to provide the global config
    def set_config(self, config):
        self.config = config

    # If this indicator is enabled
    def get_is_enabled(self):
        return self.enabled

    # implement locally if the service has thread(s) to stop
    def stop(self):
        pass

    # Returns true if all the configuration is available
    @abstractmethod
    def has_required_configuration(self):
        raise NotImplementedError("has_required_configuration not implemented")

    # Returns the service's endpoint
    @abstractmethod
    def get_endpoint(self) -> None:
        raise NotImplementedError("get_endpoint not implemented")

    # Called to put in the right service in config
    @abstractmethod
    def get_type(self) -> None:
        raise NotImplementedError("get_type not implemented")

    # Called after service setup
    @abstractmethod
    def prepare(self) -> None:
        raise NotImplementedError("prepare not implemented")
