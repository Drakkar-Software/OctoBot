from config.cst import CONFIG_ADVANCED
from evaluator.Util.abstract_util import AbstractUtil
from evaluator.abstract_evaluator import AbstractEvaluator


class AdvancedManager:
    @staticmethod
    def get_advanced(config, class_type):
        if len(class_type.__subclasses__()) > 1:
            for child in class_type.__subclasses__():
                AdvancedManager.get_advanced(config, child)
        elif len(class_type.__subclasses__()) == 1:
            AdvancedManager.set_if_not_exists_class(config, class_type.get_name(), class_type.__subclasses__()[0])
        else:
            AdvancedManager.set_if_not_exists_class(config, class_type.get_name(), class_type)

    @staticmethod
    def create_class_list(config):
        config[CONFIG_ADVANCED] = {}

        # Evaluators
        AdvancedManager.get_advanced(config, AbstractEvaluator)

        # Util
        AdvancedManager.get_advanced(config, AbstractUtil)

    @staticmethod
    def get_advanced_list(config):
        return config[CONFIG_ADVANCED]

    @staticmethod
    def set_if_not_exists_class(config, class_name, class_type):
        if class_name not in AdvancedManager.get_advanced_list(config):
            AdvancedManager.get_advanced_list(config)[class_name] = class_type

    @staticmethod
    def get_class(config, class_name):
        if class_name in AdvancedManager.get_advanced_list(config):
            return AdvancedManager.get_advanced_list(config)[class_name]
        else:
            return None
