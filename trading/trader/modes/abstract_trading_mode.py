from abc import *


class AbstractTradingMode:
    __metaclass__ = ABCMeta

    def __init__(self, config):
        self.config = config

        self.decider = None
        self.creators = {}

    def set_decider(self, decider):
        self.decider = decider

    def add_creator(self, creator, creator_key=None):
        if not creator_key:
            creator_key = creator.__class__.__name__
        self.creators[creator_key] = creator

    def get_creator(self, creator_key):
        return self.creators[creator_key]

    def get_only_creator_key(self):
        return next(iter(self.creators.keys()))

    def get_decider(self):
        return self.decider
