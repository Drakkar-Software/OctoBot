from abc import ABCMeta


class AbstractUtil:
    __metaclass__ = ABCMeta

    @classmethod
    def get_name(cls):
        return cls.__name__
