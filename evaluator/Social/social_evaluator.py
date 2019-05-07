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

import os
from abc import abstractmethod

from config.config import load_config
from config import CONFIG_EVALUATOR_SOCIAL
from evaluator.abstract_evaluator import AbstractEvaluator


class SocialEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.social_config = {}
        self.need_to_notify = False
        self.is_self_refreshing = False
        self.keep_running = True
        self.is_to_be_independently_tasked = False
        self.evaluator_task_managers = []
        self.load_config()

    @classmethod
    def get_config_tentacle_type(cls) -> str:
        return CONFIG_EVALUATOR_SOCIAL

    def stop(self):
        self.keep_running = False

    def add_evaluator_task_manager(self, evaluator_task):
        self.evaluator_task_managers.append(evaluator_task)

    async def notify_evaluator_task_managers(self, notifier_name):
        for task_manager in self.evaluator_task_managers:
            await task_manager.notify(notifier_name, finalize=True, interruption=True)

    def load_config(self):
        config_file = self.get_config_file_name()
        # try with this class name
        if os.path.isfile(config_file):
            self.social_config = load_config(config_file)
        else:
            # if it's not possible, try with any super-class' config file
            for super_class in self.get_parent_evaluator_classes(SocialEvaluator):
                super_class_config_file = super_class.get_config_file_name()
                if os.path.isfile(super_class_config_file):
                    self.social_config = load_config(super_class_config_file)
                    return
        # set default config if nothing found
        if not self.social_config:
            self.set_default_config()

    def get_is_to_be_independently_tasked(self):
        return self.is_to_be_independently_tasked

    def get_is_self_refreshing(self):
        return self.is_self_refreshing

    # to implement in subclasses if config necessary
    # required if is_to_be_independently_tasked = False --> provide evaluator refreshing time
    def set_default_config(self):
        pass

    def get_social_config(self):
        return self.social_config

    # is called just before start(), implement if necessary
    def prepare(self):
        pass

    @abstractmethod
    async def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    # get data needed to perform the eval
    # example :
    # def get_data(self):
    #   for follow in followers:
    #       self.data.append(twitter.API(XXXXX))
    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")


class StatsSocialEvaluator(SocialEvaluator):
    __metaclass__ = SocialEvaluator

    @abstractmethod
    async def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")


class ForumSocialEvaluator(SocialEvaluator):
    __metaclass__ = SocialEvaluator

    @abstractmethod
    async def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")


class NewsSocialEvaluator(SocialEvaluator):
    __metaclass__ = SocialEvaluator

    @abstractmethod
    async def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")

    @abstractmethod
    def get_data(self):
        raise NotImplementedError("Get Data not implemented")
