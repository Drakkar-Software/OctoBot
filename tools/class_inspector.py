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

import inspect


def _default_parent_inspection(element, parent):
    return parent in element.__bases__


def evaluator_parent_inspection(element, parent):
    return hasattr(element, "get_parent_evaluator_classes") and element.get_parent_evaluator_classes(parent)


def trading_mode_parent_inspection(element, parent):
    return hasattr(element, "get_parent_trading_mode_classes") and element.get_parent_trading_mode_classes(parent)


def get_class_from_string(class_string, parent, module, parent_inspection=_default_parent_inspection,
                          error_when_not_found=False):
    if any(m[0] == class_string and
           hasattr(m[1], '__bases__') and
           parent_inspection(m[1], parent)
           for m in inspect.getmembers(module)):
        return getattr(module, class_string)
    if error_when_not_found:
        raise ModuleNotFoundError(f"Cant find {class_string} module")
    return None


def get_deep_class_from_string(class_string, module):
    for m in inspect.getmembers(module):
        if m[0] == class_string:
            return getattr(module, class_string)
    return None
