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

from tools.logging.logging_util import get_logger
import os
from abc import *

from config.config import load_config
from config import CONFIG_FILE_EXT, EVALUATOR_CONFIG_FOLDER, \
    TRADING_MODE_REQUIRED_STRATEGIES, TENTACLES_PATH, TENTACLES_TRADING_PATH, TENTACLES_TRADING_MODE_PATH
from evaluator import Strategies
from evaluator.Util.advanced_manager import AdvancedManager
from tools.class_inspector import get_deep_class_from_string


class AbstractTradingMode:
    __metaclass__ = ABCMeta
    DESCRIPTION = "No description set."

    def __init__(self, config, exchange):
        self.config = config

        self.trading_config = None
        self.creators = {}
        self.deciders = {}
        self.deciders_without_keys = {}
        self.strategy_instances_by_classes = {}
        self.symbol_evaluators = {}
        self.exchange = exchange

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def get_config_file_name(cls):
        return f"{TENTACLES_PATH}/{TENTACLES_TRADING_PATH}/{TENTACLES_TRADING_MODE_PATH}/{EVALUATOR_CONFIG_FOLDER}/" \
               f"{cls.get_name() + CONFIG_FILE_EXT}"

    @classmethod
    def get_trading_mode_config(cls):
        try:
            return load_config(cls.get_config_file_name())
        except Exception as e:
            raise e

    @classmethod
    def get_required_strategies(cls):
        config = cls.get_trading_mode_config()
        if TRADING_MODE_REQUIRED_STRATEGIES in config:
            strategies_classes = []
            for class_string in config[TRADING_MODE_REQUIRED_STRATEGIES]:
                s_class = get_deep_class_from_string(class_string, Strategies)
                if s_class is not None:
                    if s_class not in strategies_classes:
                        strategies_classes.append(s_class)
                else:
                    raise Exception(f"{class_string} is not found, Octobot can't use {cls.get_name()},"
                                    f" please check {cls.get_name()}{cls.get_config_file_name()}")

            return strategies_classes
        else:
            raise Exception(f"'{TRADING_MODE_REQUIRED_STRATEGIES}' is missing in {cls.get_config_file_name()}")

    @abstractmethod
    def create_deciders(self, symbol, symbol_evaluator) -> None:
        raise NotImplementedError("create_deciders not implemented")

    @abstractmethod
    def create_creators(self, symbol, symbol_evaluator) -> None:
        raise NotImplementedError("create_creators not implemented")

    @classmethod
    # Description of the trading mode, used as documentation
    def get_description(cls):
        return cls.DESCRIPTION

    def add_symbol_evaluator(self, symbol_evaluator):
        new_symbol = symbol_evaluator.get_symbol()
        self.symbol_evaluators[new_symbol] = symbol_evaluator

        # init maps
        self.creators[new_symbol] = {}
        self.deciders[new_symbol] = {}
        self.deciders_without_keys[new_symbol] = []

        # init strategies
        self.strategy_instances_by_classes[new_symbol] = {}
        self._init_strategies_instances(new_symbol, symbol_evaluator.get_strategies_eval_list(self.exchange))

        # create decider and creators
        self.create_creators(new_symbol, symbol_evaluator)
        self.create_deciders(new_symbol, symbol_evaluator)

    def get_strategy_instances_by_classes(self, symbol):
        return self.strategy_instances_by_classes[symbol]

    def _init_strategies_instances(self, symbol, all_strategy_instances):
        all_strategy_classes = [s.__class__ for s in all_strategy_instances]
        for required_class in self.get_required_strategies():
            if required_class in all_strategy_classes:
                self.strategy_instances_by_classes[symbol][required_class] = \
                    all_strategy_instances[all_strategy_classes.index(required_class)]
            else:
                subclass = AdvancedManager.get_class(self.config, required_class)
                if subclass in all_strategy_classes:
                    self.strategy_instances_by_classes[symbol][required_class] = \
                        all_strategy_instances[all_strategy_classes.index(subclass)]
            if required_class not in self.strategy_instances_by_classes[symbol]:
                get_logger(self.get_name()).error(f"No instance of {required_class.__name__} "
                                                  f"or advanced equivalent found, {self.get_name()} trading "
                                                  "mode can't work properly ! Maybe this strategy is disabled in"
                                                  " tentacles/Evaluator/evaluator_config.json.")

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

    def add_decider(self, symbol, decider, decider_key=None):
        if not decider_key:
            decider_key = decider.__class__.__name__
            if decider_key in self.creators[symbol]:
                to_add_id = 2
                proposed_decider_key = decider_key + str(to_add_id)

                while proposed_decider_key in self.deciders[symbol]:
                    to_add_id += 1
                    proposed_decider_key = decider_key + str(to_add_id)

                decider_key = proposed_decider_key

        self.deciders[symbol][decider_key] = decider
        self.deciders_without_keys[symbol].append(decider)
        return decider_key

    def add_creator(self, symbol, creator, creator_key=None):
        if not creator_key:
            creator_key = creator.__class__.__name__
            if creator_key in self.creators[symbol]:
                to_add_id = 2
                proposed_creator_key = creator_key + str(to_add_id)

                while proposed_creator_key in self.creators[symbol]:
                    to_add_id += 1
                    proposed_creator_key = creator_key + str(to_add_id)

                creator_key = proposed_creator_key

        self.creators[symbol][creator_key] = creator
        return creator_key

    @classmethod
    def get_parent_trading_mode_classes(cls, higher_parent_class_limit=None):
        limit_class = higher_parent_class_limit if higher_parent_class_limit else AbstractTradingMode

        return [
            class_type
            for class_type in cls.mro()
            if limit_class in class_type.mro()
        ]

    def get_creator(self, symbol, creator_key):
        return self.creators[symbol][creator_key]

    def get_creators(self, symbol):
        return self.creators[symbol]

    def get_only_creator_key(self, symbol):
        return next(iter(self.creators[symbol].keys()))

    def get_only_decider_key(self, symbol, with_keys=False):
        if with_keys:
            return next(iter(self.deciders[symbol].keys()))
        else:
            return self.deciders_without_keys[symbol][0]

    def get_decider(self, symbol, decider_key):
        return self.deciders[symbol][decider_key]

    def get_deciders(self, symbol, with_keys=False):
        if with_keys:
            return self.deciders[symbol]
        else:
            return self.deciders_without_keys[symbol]
