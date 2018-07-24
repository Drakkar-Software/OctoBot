import inspect


def _default_parent_inspection(element, parent):
    return parent in element.__bases__


def evaluator_parent_inspection(element, parent):
    return element.get_parent_evaluator_classes(parent)


def get_class_from_string(class_string, parent, module, parent_inspection=_default_parent_inspection):
    if any(m[0] == class_string and
           hasattr(m[1], '__bases__') and
           parent_inspection(m[1], parent)
           for m in inspect.getmembers(module)):
        return getattr(module, class_string)
    return None


def get_deep_class_from_string(class_string, module):
    for m in inspect.getmembers(module):
        if m[0] == class_string:
            return getattr(module, class_string)
    return None
