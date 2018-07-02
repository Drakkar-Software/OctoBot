import logging
import os
from abc import *

from config.config import load_config
from config.cst import CONFIG_FILE_EXT, EVALUATOR_CONFIG_FOLDER, \
    TRADING_MODE_REQUIRED_STRATEGIES, TENTACLES_PATH, TENTACLES_TRADING_PATH, TENTACLES_TRADING_MODE_PATH
from evaluator import Strategies
from evaluator.Util.advanced_manager import AdvancedManager
from tools.class_inspector import get_deep_class_from_string


class AbstractTradingMode:
    __metaclass__ = ABCMeta

    def __init__(self, config, symbol_evaluator, exchange):
        self.config = config

        self.trading_config = None
        self.creators = {}
        self.deciders = {}
        self.deciders_without_keys = []
        self.strategy_instances_by_classes = {}
        self.symbol = symbol_evaluator.get_symbol()
        self._init_strategies_instances(symbol_evaluator.get_strategies_eval_list(exchange))

    @classmethod
    def get_required_strategies(cls):
        config = cls.get_trading_mode_config()
        if TRADING_MODE_REQUIRED_STRATEGIES in config:
            strategies_classes = []
            for class_string in config[TRADING_MODE_REQUIRED_STRATEGIES]:
                r = get_deep_class_from_string(class_string, Strategies)
                if r is not None:
                    if r not in strategies_classes:
                        strategies_classes.append(r)
                else:
                    raise Exception("{0} is not found, Octobot can't use {1}, please check {1}{2}".format(
                        class_string,
                        cls.get_name(),
                        cls.get_config_file_name()))

            return strategies_classes
        else:
            raise Exception("'{0}' is missing in {1}".format(TRADING_MODE_REQUIRED_STRATEGIES,
                                                             cls.get_config_file_name()))

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def get_config_file_name(cls):
        return "{0}/{1}/{2}/{3}/{4}".format(TENTACLES_PATH, TENTACLES_TRADING_PATH, TENTACLES_TRADING_MODE_PATH
                                            , EVALUATOR_CONFIG_FOLDER, cls.get_name() + CONFIG_FILE_EXT)

    @classmethod
    def get_trading_mode_config(cls):
        try:
            return load_config(cls.get_config_file_name())
        except Exception as e:
            raise e

    def get_strategy_instances_by_classes(self):
        return self.strategy_instances_by_classes

    def _init_strategies_instances(self, all_strategy_instances):
        all_strategy_classes = [s.__class__ for s in all_strategy_instances]
        for required_class in self.get_required_strategies():
            if required_class in all_strategy_classes:
                self.strategy_instances_by_classes[required_class] = \
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

    def add_decider(self, decider, decider_key=None):
        if not decider_key:
            decider_key = decider.__class__.__name__
            if decider_key in self.creators:
                to_add_id = 2
                proposed_decider_key = decider_key + str(to_add_id)
                while proposed_decider_key in self.deciders:
                    to_add_id += 1
                    proposed_decider_key = decider_key + str(to_add_id)
                decider_key = proposed_decider_key
        self.deciders[decider_key] = decider
        self.deciders_without_keys.append(decider)
        return decider_key

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
        return creator_key

    def get_creator(self, creator_key):
        return self.creators[creator_key]

    def get_creators(self):
        return self.creators

    def get_only_creator_key(self):
        return next(iter(self.creators.keys()))

    def get_only_decider_key(self, with_keys=False):
        if with_keys:
            return next(iter(self.deciders.keys()))
        else:
            return self.deciders_without_keys[0]

    def get_decider(self, decider_key):
        return self.deciders[decider_key]

    def get_deciders(self, with_keys=False):
        if with_keys:
            return self.deciders
        else:
            return self.deciders_without_keys
