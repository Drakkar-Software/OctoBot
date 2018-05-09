from config.cst import CONFIG_ADVANCED_CLASSES, CONFIG_ADVANCED_INSTANCES
from evaluator.Util.abstract_util import AbstractUtil
from evaluator.abstract_evaluator import AbstractEvaluator
import logging


class AdvancedManager:

    """ is_abstract will test if the class in an abstract one or not
    by checking if __metaclass__ attribute is inherited or not we will know if the class is an abstract one

    Returns True if it is an abstract one else False. """
    @staticmethod
    def is_abstract(class_type):
        # Get class parental description
        mro = class_type.mro()

        # if class has parent get its metaclass
        try:
            parent_metaclass = mro[1].__metaclass__
        except KeyError:
            parent_metaclass = None

        # If the metaclass attribute has been inherited
        try:
            if class_type.__metaclass__ == parent_metaclass:
                return False
            else:
                return True
        except AttributeError:
            return False

    """ get_advanced will get each subclasses of the parameter class_type
    For each abstract subclasses it will call itself with the reference abstract_class not set
    If the current child is not abstract it will be set as the reference only if abstract_class is None
    If there is not subclasses to class_type it will add class_type into the config advanced list 
    with its name as a key or the reference class name --> abstract_class
    """
    @staticmethod
    def _get_advanced(config, class_type, abstract_class=None):
        if len(class_type.__subclasses__()) > 0:
            for child in class_type.__subclasses__():
                if AdvancedManager.is_abstract(child):
                    AdvancedManager._get_advanced(config, child)
                else:
                    # If abstract class is not defined --> current non abstract_class is the reference
                    # else keep the first non abstract class as the reference
                    if abstract_class is None:
                        AdvancedManager._get_advanced(config, child, child.get_name())
                    else:
                        AdvancedManager._get_advanced(config, child, abstract_class)
        else:
            if abstract_class is not None:
                AdvancedManager._append_to_class_list(config, abstract_class, class_type)
            else:
                AdvancedManager._append_to_class_list(config, class_type.get_name(), class_type)

    """ create_class_list will create a list with the best class available
    Advanced class are declared into advanced folders of each packages
    For AbstractEvaluator and AbstractUtil classes, this will call the get_advanced method to initialize the config list
    """
    @staticmethod
    def create_class_list(config):
        config[CONFIG_ADVANCED_CLASSES] = {}
        config[CONFIG_ADVANCED_INSTANCES] = {}

        # Evaluators
        AdvancedManager._get_advanced(config, AbstractEvaluator)

        # Util
        AdvancedManager._get_advanced(config, AbstractUtil)

    @staticmethod
    def _get_advanced_classes_list(config):
        return config[CONFIG_ADVANCED_CLASSES]

    @staticmethod
    def _get_advanced_instances_list(config):
        return config[CONFIG_ADVANCED_INSTANCES]

    @staticmethod
    def _append_to_class_list(config, class_name, class_type):
        if class_name not in AdvancedManager._get_advanced_classes_list(config):
            AdvancedManager._get_advanced_classes_list(config)[class_name] = [class_type]
        else:
            AdvancedManager._get_advanced_classes_list(config)[class_name].append(class_type)

    @staticmethod
    def get_classes(config, class_type):
        if class_type.get_name() in AdvancedManager._get_advanced_classes_list(config):
            return AdvancedManager._get_advanced_classes_list(config)[class_type.get_name()]
        else:
            return [class_type]

    @staticmethod
    def get_class(config, class_type):
        classes = AdvancedManager.get_classes(config, class_type)
        if classes and len(classes) > 1:
            logging.getLogger(AdvancedManager.__name__).warning("More than one instance of {0} available, using {1}.".
                                                                format(class_type, classes[0]))
        return classes[0]

    @staticmethod
    def get_util_instance(config, class_type, *args):
        advanced_class_type = AdvancedManager.get_class(config, class_type)
        if class_type in AdvancedManager._get_advanced_instances_list(config):
            return AdvancedManager._get_advanced_instances_list(config)[class_type]
        elif advanced_class_type:
            instance = advanced_class_type(*args)
            AdvancedManager._get_advanced_instances_list(config)[class_type] = instance
            return instance
        return None

    @staticmethod
    def create_advanced_evaluator_types_list(evaluator_class, config):
        evaluator_advanced_eval_class_list = []
        for evaluator_subclass in evaluator_class.__subclasses__():
            for eval_class in evaluator_subclass.__subclasses__():
                for eval_class_type in AdvancedManager.get_classes(config, eval_class):
                    evaluator_advanced_eval_class_list.append(eval_class_type)
        return evaluator_advanced_eval_class_list
