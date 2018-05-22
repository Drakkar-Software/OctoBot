import logging
from services.abstract_service import *
from config.cst import *


class ServiceCreator:

    @classmethod
    def get_name(cls):
        return cls.__name__

    @staticmethod
    def create_services(config):
        logger = logging.getLogger(ServiceCreator.get_name())
        for service_class in AbstractService.__subclasses__():
            service_instance = service_class()
            if service_instance.get_is_enabled():
                service_instance.set_logger(logging.getLogger(service_class.get_name()))
                service_instance.set_config(config)
                if service_instance.has_required_configuration():
                    try:
                        service_instance.prepare()
                        config[CONFIG_CATEGORY_SERVICES][service_instance.get_type()][CONFIG_SERVICE_INSTANCE] = \
                            service_instance
                        service_instance.say_hello()
                    except Exception as e:
                        logger.error(service_class.get_name() + " preparation produced the following error: " + str(e))
                else:
                    if service_instance.get_should_warn():
                        logger.warning(service_class.get_name() + " can't be initialized: configuration is missing !")

    @staticmethod
    def get_service_instances(config):
        instances = []
        for services in config[CONFIG_CATEGORY_SERVICES]:
            if CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][services]:
                instances.append(config[CONFIG_CATEGORY_SERVICES][services][CONFIG_SERVICE_INSTANCE])
        return instances
