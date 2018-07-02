import inspect


def get_class_from_string(class_string, parent, module):
    if any(m[0] == class_string and
           hasattr(m[1], '__bases__') and
           parent in m[1].__bases__
           for m in inspect.getmembers(module)):
        return getattr(module, class_string)
    return None


def get_deep_class_from_string(class_string, module):
    for m in inspect.getmembers(module):
        if m[0] == class_string:
            return getattr(module, class_string)
    return None
