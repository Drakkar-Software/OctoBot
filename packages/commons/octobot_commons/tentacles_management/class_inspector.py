#  Drakkar-Software OctoBot-Commons
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
import inspect

import octobot_commons.logging as logging_util


def default_parent_inspection(element, parent):
    """
    Check if the element bases has the specified parent
    :param element: the element to check
    :param parent: the expected parent
    :return: the check result
    """
    return parent in element.__bases__


def default_parents_inspection(element, parent):
    """
    Check if the element has the specified parent
    :param element: the element to check
    :param parent: the expected parent
    :return: the check result
    """
    return parent in element.mro()


def evaluator_parent_inspection(element, parent):
    """
    Recursively check if the evaluator class has the specified parent
    :param element: the element to check
    :param parent: the expected parent
    :return: the check result
    """
    return hasattr(
        element, "get_parent_evaluator_classes"
    ) and element.get_parent_evaluator_classes(parent)


def trading_mode_parent_inspection(element, parent):
    """
    Check if the trading class has the specified parent
    :param element: the element to check
    :param parent: the expected parent
    :return: the check result
    """
    return hasattr(
        element, "get_parent_trading_mode_classes"
    ) and element.get_parent_trading_mode_classes(parent)


def get_class_from_parent_subclasses(class_string, parent):
    """
    Search the class string in parent subclasses
    :param class_string: the class name to search
    :param parent: the parent
    :return: the class if found else None
    """
    for found in parent.__subclasses__():
        if found.__name__ == class_string:
            return found
    return None


def get_deep_class_from_parent_subclasses(class_string, parent):
    """
    Search for a class in parent subclasses "deeply"
    :param class_string: the class name to search
    :param parent: the expected parent
    :return: the class if found else None
    """
    found = get_class_from_parent_subclasses(class_string, parent)
    if found is not None:
        return found

    for parent_class in parent.__subclasses__():
        found = get_deep_class_from_parent_subclasses(class_string, parent_class)
        if found is not None:
            return found
    return None


def get_class_from_string(
    class_string: str,
    parent,
    module,
    parent_inspection=default_parent_inspection,
    error_when_not_found: bool = False,
):
    """
    Search a class from a class string in a specified module for a specified parent
    :param class_string: the class name to search
    :param parent: the class expected parent
    :param module: the class expected module
    :param parent_inspection: the parent inspection
    :param error_when_not_found: if errors should be raised
    :return: the class if found else None
    """
    if tentacle_class_by_name := {
        m[0]: m[1]
        for m in inspect.getmembers(module)
        if (m[0] == class_string)
        and hasattr(m[1], "__bases__")
        and parent_inspection(m[1], parent)
    }:
        return tentacle_class_by_name[class_string]
    if error_when_not_found:
        raise ModuleNotFoundError(f"Cant find {class_string} module")
    return None  # no class found


def is_abstract_using_inspection_and_class_naming(clazz):
    """
    Check if a class is abstract
    :param clazz: the class to check
    :return: the check result
    """
    return inspect.isabstract(clazz) or "abstract" in clazz.__name__.lower()


def get_all_classes_from_parent(parent_class) -> list:
    """
    Get all sub classes from parent including multi level sub-classes
    :param parent_class: the parent class
    :return: the class from parent
    """
    classes = []
    for subclass in parent_class.__subclasses__():
        if subclass.__subclasses__():
            # append this subclass
            classes.append(subclass)

            # and all its subclasses
            classes += get_all_classes_from_parent(subclass)
        else:
            classes.append(subclass)
    return classes


def get_single_deepest_child_class(clazz) -> object:
    """
    Get the single deepest child class
    :param clazz: the class
    :return: the single deepest child class
    """
    children_classes = clazz.__subclasses__()
    if len(children_classes) == 0:
        return clazz
    if len(children_classes) > 1:
        logging_util.get_logger(__name__).error(
            f"More than one child class of {clazz}, expecting one, "
            f"using {children_classes[0]}"
        )
    return get_single_deepest_child_class(children_classes[0])
