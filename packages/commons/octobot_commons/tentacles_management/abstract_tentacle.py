# pylint: disable=C0103,W0703,C0415
#  Drakkar-Software OctoBot-Commons
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
import abc
import copy


import octobot_commons.enums as commons_enums
import octobot_commons.configuration.user_inputs as user_inputs
import octobot_commons.configuration as configuration


class AbstractTentacle:
    """
    The parent class of any OctoBot tentacle
    """

    __metaclass__ = abc.ABCMeta

    ALLOW_SUPER_CLASS_CONFIG = (
        False  # when True, the given tentacle can read its parent class configuration
    )
    USER_INPUT_TENTACLE_TYPE = (
        commons_enums.UserInputTentacleTypes.UNDEFINED
    )  # tentacle type, saved in user inputs
    HISTORIZE_USER_INPUT_CONFIG = (
        False  # when True, user input values can be saved and read from the run data db
    )
    CLASS_UI = user_inputs.UserInputFactory(
        commons_enums.UserInputTentacleTypes.UNDEFINED
    )  # class-level user input factory. Used when initializing user inputs with classmethods

    def __init__(self):
        self.logger = None
        self.UI: user_inputs.UserInputFactory = user_inputs.UserInputFactory(
            self.USER_INPUT_TENTACLE_TYPE
        )
        self.UI.set_tentacle_class(self.__class__).set_tentacle_config_proxy(
            self.get_local_config
        )

    @classmethod
    def get_name(cls) -> str:
        """
        Tentacle name based on class name
        :return: the tentacle name
        """
        return cls.__name__

    @classmethod
    def get_all_subclasses(cls) -> list:
        """
        Return all subclasses of this tentacle
        :return: the subclasses
        """
        subclasses_list = cls.__subclasses__()
        if cls.__subclasses__():
            for subclass in copy.deepcopy(subclasses_list):
                subclasses_list += subclass.get_all_subclasses()
        return subclasses_list

    @classmethod
    def is_configurable(cls):
        """
        Override if the tentacle is allowed to be configured
        """
        return True

    @classmethod
    def get_user_commands(cls) -> dict:
        """
        Return the dict of user commands for this tentacle
        :return: the commands dict
        """
        return {}

    def get_local_config(self):
        """
        Implementation required if cls.HISTORIZE_USER_INPUT_CONFIG is True
        :return: the config of the tentacle
        """
        raise NotImplementedError

    @classmethod
    def create_local_instance(cls, config, tentacles_setup_config, tentacle_config):
        """
        Implementation required if cls.HISTORIZE_USER_INPUT_CONFIG is True
        :param config: the global configuration to give to the tentacle
        :param tentacles_setup_config: the global tentacles setup configuration to give to the tentacle
        :param tentacle_config: the tentacle configuration to give to the tentacle
        :return: a local, aimed to be short-lived, tentacle instance
        """
        raise NotImplementedError

    def init_user_inputs(self, inputs: dict) -> None:
        """
        instance method API for user inputs. Used by load_and_save_user_inputs
        Override if this tentacle has user inputs that should be initialized on a specific instance
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """

    @classmethod
    def init_user_inputs_from_class(cls, inputs: dict) -> None:
        """
        classmethod API for user inputs. Used by init_user_inputs_from_class
        Override if this tentacle has user inputs that can be initialized on a class level
        Called by load_user_inputs_from_class, should define all the tentacle user inputs.
        """

    async def load_and_save_user_inputs(self, bot_id: str) -> dict:
        """
        instance method API for user inputs
        Initialize and save the tentacle user inputs in run data
        :return: the filled user input configuration
        """
        return await configuration.load_and_save_user_inputs(self, bot_id)

    @classmethod
    def load_user_inputs_from_class(
        cls, tentacles_setup_config, tentacle_config
    ) -> dict:
        """
        classmethod API for user inputs
        Initialize the tentacle user inputs
        Called by get_raw_config_and_user_inputs
        """
        return configuration.load_user_inputs_from_class(
            cls, tentacles_setup_config, tentacle_config
        )

    @classmethod
    async def get_raw_config_and_user_inputs(
        cls, config, tentacles_setup_config, bot_id
    ):
        """
        :return: the tentacle configuration and its list of user inputs
        """
        if not cls.HISTORIZE_USER_INPUT_CONFIG:
            return configuration.get_raw_config_and_user_inputs_from_class(
                cls, tentacles_setup_config
            )
        return await configuration.get_raw_config_and_user_inputs(
            cls, config, tentacles_setup_config, bot_id
        )

    @classmethod
    def get_tentacle_config_traded_symbols(
        cls, config: dict, reference_market: str
    ) -> list:
        """
        :return: the traded symbols of the tentacle according to its tentacle configuration
        """
        raise NotImplementedError(
            "get_tentacle_config_traded_symbols is not implemented"
        )
