import os
import logging
from abc import *

from config.config import load_config
from config.cst import CONFIG_FILE_EXT, CONFIG_TRADING, CONFIG_TRADER, CONFIG_TRADER_MODES, EVALUATOR_CONFIG_FOLDER
from evaluator.Util.advanced_manager import AdvancedManager


class AbstractTradingMode:
    __metaclass__ = ABCMeta

    def __init__(self, config, symbol_evaluator, exchange):
        self.config = config

        self.decider = None
        self.trading_config = None
        self.creators = {}
        self.strategy_instances_by_classes = {}
        self._init_strategies_instances(symbol_evaluator.get_strategies_eval_list(exchange))

    @staticmethod
    @abstractmethod
    def get_required_strategies():
        raise NotImplementedError("get_required_strategies not implemented")

    def set_decider(self, decider):
        self.decider = decider

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def get_config_file_name(cls):
        return "{0}/{1}/{2}/{3}/{4}".format(CONFIG_TRADING, CONFIG_TRADER, CONFIG_TRADER_MODES, EVALUATOR_CONFIG_FOLDER,
                                            cls.get_name() + CONFIG_FILE_EXT)

    def get_strategy_instances_by_classes(self):
        return self.strategy_instances_by_classes

    def _init_strategies_instances(self, all_strategy_instances):
        all_strategy_classes = [s.__class__ for s in all_strategy_instances]
        for required_class in self.get_required_strategies():
            if required_class in all_strategy_classes:
                self.strategy_instances_by_classes[required_class]=\
                    all_strategy_instances[all_strategy_classes.index(required_class)]
            else:
                subclass = AdvancedManager.get_class(self.config, required_class)
                if subclass in all_strategy_classes:
                    self.strategy_instances_by_classes[required_class] = \
                        all_strategy_instances[all_strategy_classes.index(subclass)]
            if required_class not in self.strategy_instances_by_classes:
                logging.getLogger(self.get_name()).error("No instance of {} or advanced equivalent found, {} trading "
                                                         "mode can't work properly ! Maybe this strategy is disabled in"
                                                         " tentacles/Evaluator/evaluator_config.json."
                                                         .format(required_class.__name__, self.get_name()))

    def load_config(self):
        config_file = self.get_config_file_name()
        # try with this class name
        if os.path.isfile(config_file):
            self.trading_config = load_config(config_file)

        # set default config if nothing found
        if not self.trading_config:
            self.set_default_config()

    # to implement in subclasses if config necessary
    def set_default_config(self):
        pass

    def add_creator(self, creator, creator_key=None):
        if not creator_key:
            creator_key = creator.__class__.__name__
            if creator_key in self.creators:
                to_add_id = 2
                proposed_creator_key = creator_key + str(to_add_id)
                while proposed_creator_key in self.creators:
                    to_add_id += 1
                    proposed_creator_key = creator_key + str(to_add_id)
                creator_key = proposed_creator_key
        self.creators[creator_key] = creator

    def get_creator(self, creator_key):
        return self.creators[creator_key]

    def get_only_creator_key(self):
        return next(iter(self.creators.keys()))

    def get_creators(self):
        return self.creators

    def get_decider(self):
        return self.decider
