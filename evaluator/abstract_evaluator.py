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

import copy
import time
from abc import *

from config.config import load_config

from config import *
from evaluator.Dispatchers.abstract_dispatcher import DispatcherAbstractClient
from tools.config_manager import ConfigManager


class AbstractEvaluator:
    __metaclass__ = ABCMeta

    DESCRIPTION = "No description set."

    def __init__(self):
        super().__init__()
        self.logger = None
        self.config = None
        self.enabled = True
        self.symbol = None
        self.history_time = None

        self.eval_note = START_PENDING_EVAL_NOTE
        self.pertinence = START_EVAL_PERTINENCE

        self.eval_note_time_to_live = None
        self.eval_note_changed_time = None

        self.is_active = True

        self.is_to_be_started_as_task = False

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def get_all_subclasses(cls):
        subclasses_list = cls.__subclasses__()
        if subclasses_list:
            for subclass in copy.deepcopy(subclasses_list):
                subclasses_list += subclass.get_all_subclasses()
        return subclasses_list

    @classmethod
    def get_config_file_name(cls, config_evaluator_type=None):
        return f"{TENTACLES_PATH}/{TENTACLES_EVALUATOR_PATH}/{config_evaluator_type}/{EVALUATOR_CONFIG_FOLDER}" \
            f"/{cls.get_name() + CONFIG_FILE_EXT}"

    @classmethod
    def get_evaluator_config(cls):
        try:
            return load_config(cls.get_config_file_name())
        except Exception as e:
            raise e

    # Used to provide a new logger for this particular indicator
    def set_logger(self, logger):
        self.logger = logger

    # Used to provide the global config
    def set_config(self, config):
        self.config = config
        self.enabled = self.is_enabled(config, False)

    # Symbol is the cryptocurrency symbol
    def set_symbol(self, symbol):
        self.symbol = symbol

    # Active tells if this evalautor is currently activated (an evaluator can be paused)
    def set_is_active(self, is_active):
        self.is_active = is_active

    # history time represents the period of time of the indicator
    def set_history_time(self, history_time):
        self.history_time = history_time

    # Eval note will be set by the eval_impl at each call
    def get_eval_note(self):
        return self.eval_note

    # set to true if start_task has to be called to start evaluator
    def set_is_to_be_started_as_task(self, value):
        self.is_to_be_started_as_task = value

    # Pertinence of indicator will be used with the eval_note to provide a relevancy
    def get_pertinence(self):
        return self.pertinence

    @classmethod
    # Description of the evaluator, used as documentation
    def get_description(cls):
        return cls.DESCRIPTION

    # If this indicator is enabled
    def get_is_enabled(self):
        return self.enabled

    # Active tells if this evaluator is currently activated (an evaluator can be paused)
    def get_is_active(self):
        return self.is_active

    # Return the evaluator symbol
    def get_symbol(self):
        return self.symbol

    def get_is_to_be_started_as_task(self):
        return self.is_to_be_started_as_task

    # generic eval that will call the indicator eval_impl()
    async def eval(self) -> None:
        try:
            self.ensure_eval_note_is_not_expired()
            await self.eval_impl()
        except Exception as e:
            if ConfigManager.is_in_dev_mode(self.config):
                raise e
            else:
                self.logger.error("Exception in eval_impl(): " + str(e))
        finally:
            if self.eval_note == "nan":
                self.eval_note = START_PENDING_EVAL_NOTE
                self.logger.warning(str(self.symbol) + " evaluator returned 'nan' as eval_note, ignoring this value.")

    # eval new data
    # Notify if new data is relevant
    # example :
    # def eval_impl(self):
    #   for post in post_selected
    #       note = sentiment_evaluator(post.text)
    #       if(note > 10 || note < 0):
    #           self.need_to_notify = True
    #       self.eval_note += note
    @abstractmethod
    async def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    # reset temporary parameters to enable fresh start
    def reset(self) -> None:
        self.eval_note = START_PENDING_EVAL_NOTE

    # explore up to the 1st parent
    @classmethod
    def get_is_dispatcher_client(cls):
        if DispatcherAbstractClient in cls.__bases__:
            return True
        else:
            return any(DispatcherAbstractClient in base.__bases__ for base in cls.__bases__)

    @classmethod
    def get_parent_evaluator_classes(cls, higher_parent_class_limit=None):
        limit_class = higher_parent_class_limit if higher_parent_class_limit else AbstractEvaluator

        return [
            class_type
            for class_type in cls.mro()
            if limit_class in class_type.mro()
        ]

    def set_eval_note(self, new_eval_note):
        self.eval_note_changed()
        if self.eval_note == START_PENDING_EVAL_NOTE:
            self.eval_note = INIT_EVAL_NOTE

        if self.eval_note + new_eval_note > 1:
            self.eval_note = 1
        elif self.eval_note + new_eval_note < -1:
            self.eval_note = -1
        else:
            self.eval_note += new_eval_note

    @classmethod
    def is_enabled(cls, config, default):
        if config[CONFIG_EVALUATOR] is not None:
            if cls.get_name() in config[CONFIG_EVALUATOR]:
                return config[CONFIG_EVALUATOR][cls.get_name()]
            else:
                for parent in cls.mro():
                    if parent.__name__ in config[CONFIG_EVALUATOR]:
                        return config[CONFIG_EVALUATOR][parent.__name__]
                return default

    # use only if the current evaluation is to stay for a pre-defined amount of seconds
    def save_evaluation_expiration_time(self, eval_note_time_to_live, eval_note_changed_time=None):
        self.eval_note_time_to_live = eval_note_time_to_live
        self.eval_note_changed_time = eval_note_changed_time if eval_note_changed_time else time.time()

    def eval_note_changed(self):
        if self.eval_note_time_to_live is not None:
            if self.eval_note_changed_time is None:
                self.eval_note_changed_time = time.time()

    def ensure_eval_note_is_not_expired(self):
        if self.eval_note_time_to_live is not None:
            if self.eval_note_changed_time is None:
                self.eval_note_changed_time = time.time()

            if time.time() - self.eval_note_changed_time > self.eval_note_time_to_live:
                self.eval_note = START_PENDING_EVAL_NOTE
                self.eval_note_time_to_live = None
                self.eval_note_changed_time = None

    # async task that can be use get_data to provide real time data
    # will ONLY be called if self.is_to_be_started_as_task is set to True
    # example :
    # def start_task(self):
    #     while True:
    #         self.get_data()                           --> pull the new data
    #         self.eval()                               --> create a notification if necessary
    #         await asyncio.sleep(own_time * MINUTE_TO_SECONDS)  --> use its own refresh time

    @abstractmethod
    async def start_task(self) -> None:
        raise NotImplementedError("start_task not implemented")
