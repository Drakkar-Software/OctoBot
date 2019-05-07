#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from copy import copy

from config import CONFIG_ADVANCED_CLASSES, CONFIG_ADVANCED_INSTANCES
from tools.logging.logging_util import get_logger
from evaluator.Util.abstract_util import AbstractUtil
from evaluator.abstract_evaluator import AbstractEvaluator


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
        if class_type.__subclasses__():
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
        from trading.trader.modes.abstract_trading_mode import AbstractTradingMode

        config[CONFIG_ADVANCED_CLASSES] = {}
        config[CONFIG_ADVANCED_INSTANCES] = {}

        # Evaluators
        AdvancedManager._get_advanced(config, AbstractEvaluator)

        # Util
        AdvancedManager._get_advanced(config, AbstractUtil)

        # Trading modes
        AdvancedManager._get_advanced(config, AbstractTradingMode)

    @staticmethod
    def init_advanced_classes_if_necessary(config):
        if CONFIG_ADVANCED_CLASSES not in config:
            AdvancedManager.create_class_list(config)

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
    def get_classes(config, class_type, get_all_classes=False):
        classes = []
        if class_type.get_name() in AdvancedManager._get_advanced_classes_list(config):
            classes = copy(AdvancedManager._get_advanced_classes_list(config)[class_type.get_name()])
        if not classes or (get_all_classes and class_type not in classes):
            classes.append(class_type)
        return classes

    @staticmethod
    def get_class(config, class_type):
        classes = AdvancedManager.get_classes(config, class_type)
        if classes and len(classes) > 1:
            get_logger(AdvancedManager.__name__).warning(f"More than one instance of {class_type} available, "
                                                         f"using {classes[0]}.")
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
    def create_default_types_list(clazz):
        default_class_list = []
        for current_subclass in clazz.__subclasses__():
            subclasses = current_subclass.__subclasses__()
            if subclasses:
                for current_class in subclasses:
                    default_class_list.append(current_class)
            else:
                if not AdvancedManager.is_abstract(current_subclass):
                    default_class_list.append(current_subclass)
        return default_class_list

    @staticmethod
    def create_advanced_evaluator_types_list(evaluator_class, config):
        evaluator_advanced_eval_class_list = []
        for evaluator_subclass in evaluator_class.__subclasses__():
            for eval_class in evaluator_subclass.__subclasses__():
                for eval_class_type in AdvancedManager.get_classes(config, eval_class):
                    evaluator_advanced_eval_class_list.append(eval_class_type)

        if not AdvancedManager._check_duplicate(evaluator_advanced_eval_class_list):
            get_logger(AdvancedManager.__name__).warning("Duplicate evaluator name.")

        return evaluator_advanced_eval_class_list

    @staticmethod
    def get_all_classes(evaluator_class, config):
        evaluator_all_classes_list = []
        for evaluator_subclass in evaluator_class.__subclasses__():
            for eval_class in evaluator_subclass.__subclasses__():
                for eval_class_type in AdvancedManager.get_classes(config, eval_class, True):
                    evaluator_all_classes_list.append(eval_class_type)
        return evaluator_all_classes_list

    @staticmethod
    def _check_duplicate(list_to_check):
        return len(set(list_to_check)) == len(list_to_check)
