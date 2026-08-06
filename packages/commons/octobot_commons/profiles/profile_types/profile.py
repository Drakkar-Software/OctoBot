# pylint: disable=R0902,W0703,C0116,W0212,C0415,R0904,R0401
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
from __future__ import annotations

import copy
import os
import typing
import uuid
import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.logging as commons_logging
import octobot_commons.json_util as json_util
import octobot_commons.errors as errors
import octobot_commons.profiles.profile_edit_gate as profile_edit_gate_module


class Profile:
    """
    A profile is managing an OctoBot local configuration: activated tentacles, exchanges, currencies and
    trading settings.
    """

    FULLY_MANAGED_ELEMENTS = [
        constants.CONFIG_DISTRIBUTION,
        constants.CONFIG_CRYPTO_CURRENCIES,
        constants.CONFIG_TRADING,
        constants.CONFIG_TRADER,
        constants.CONFIG_SIMULATOR,
    ]
    PARTIALLY_MANAGED_ELEMENTS = {
        constants.CONFIG_EXCHANGES: {
            constants.CONFIG_EXCHANGE_KEY: constants.DEFAULT_API_KEY,
            constants.CONFIG_EXCHANGE_SECRET: constants.DEFAULT_API_SECRET,
            constants.CONFIG_EXCHANGE_PASSWORD: constants.DEFAULT_API_PASSWORD,
            constants.CONFIG_ENABLED_OPTION: False,
            constants.CONFIG_EXCHANGE_TYPE: constants.DEFAULT_EXCHANGE_TYPE,
        }
    }
    PARTIALLY_MANAGED_ELEMENTS_FORCED_DEFAULT_KEYS = {
        constants.CONFIG_EXCHANGES: {
            constants.CONFIG_ENABLED_OPTION: False,
        }
    }
    PARTIALLY_MANAGED_ELEMENTS_ALLOWED_KEYS = {
        constants.CONFIG_EXCHANGES: [
            constants.CONFIG_ENABLED_OPTION,
            constants.CONFIG_EXCHANGE_TYPE,
        ]
    }

    def __init__(self, profile_path: str, schema_path: str = None):
        self.profile_id: str = None
        self.path: str = profile_path
        self.schema_path: str = schema_path or constants.PROFILE_FILE_SCHEMA
        self.name: str = None
        self.slug: str = None
        self.description: str = None
        self.avatar: str = None
        self.avatar_path: str = None
        self.origin_url: str = None
        self.auto_update: bool = False
        self.read_only: bool = False
        self.hidden: bool = False
        self.imported: bool = False
        self.complexity: enums.ProfileComplexity = enums.ProfileComplexity.MEDIUM
        self.risk: enums.ProfileRisk = enums.ProfileRisk.MODERATE
        self.profile_type: enums.ProfileType = enums.ProfileType.LIVE
        self.extra_backtesting_time_frames = []

        self.config: dict = {}
        self.tentacles_setup_config = None
        self._profile_storage = None

    def bind_profile_storage(self, profile_storage) -> None:
        self._profile_storage = profile_storage

    def get_profile_storage(self):
        return self._profile_storage

    def is_strategy_locked(self) -> bool:
        profile_storage = self._profile_storage
        if profile_storage is None:
            return self.read_only
        return profile_storage.edit_gate.is_strategy_locked(self)

    def get_writable_profile_path(self) -> str:
        profile_storage = self._require_profile_storage()
        return profile_storage.edit_gate.resolve_writable_path(
            self, profile_edit_gate_module.ProfileEditType.TENTACLE_CONFIG
        )

    def get_tentacles_config_read_path(self) -> str:
        profile_storage = self._profile_storage
        if profile_storage is None:
            return self.get_tentacles_config_path()
        return profile_storage.edit_gate.resolve_activation_read_path(self)

    def _require_profile_storage(self):
        profile_storage = self._profile_storage
        if profile_storage is None:
            raise errors.ProfileDataError("ProfileStorage is not bound to this profile")
        return profile_storage

    def is_sync_backed(self) -> bool:
        return False

    def is_profile_data_tentacle_backed(self) -> bool:
        return False

    def get_storage_source(self):
        return enums.ProfileSource.FILESYSTEM

    @classmethod
    def from_profile_data(
        cls,
        profile_data,
        to_create_profile_path: str,
    ) -> Profile:
        profile = cls(to_create_profile_path)
        profile.from_dict(profile_data._to_profile_dict())
        return profile

    def from_dict(self, profile_dict: dict):
        """
        Reads a profile from the given dict
        :return: self
        """
        profile_config = profile_dict.get(constants.CONFIG_PROFILE, {})
        self.profile_id = profile_config.get(constants.CONFIG_ID, str(uuid.uuid4()))
        self.name = profile_config.get(constants.CONFIG_NAME, "")
        self.slug = profile_config.get(constants.CONFIG_SLUG, "")
        self.description = profile_config.get(constants.CONFIG_DESCRIPTION, "")
        self.avatar = profile_config.get(constants.CONFIG_AVATAR, "")
        self.origin_url = profile_config.get(constants.CONFIG_ORIGIN_URL, None)
        self.auto_update = profile_config.get(constants.CONFIG_AUTO_UPDATE, False)
        self.read_only = profile_config.get(constants.CONFIG_READ_ONLY, False)
        self.hidden = profile_config.get(constants.CONFIG_HIDDEN, False)
        self.imported = profile_config.get(constants.CONFIG_IMPORTED, False)
        self.complexity = enums.ProfileComplexity(
            profile_config.get(constants.CONFIG_COMPLEXITY)
            or enums.ProfileComplexity.MEDIUM.value
        )
        self.risk = enums.ProfileRisk(
            profile_config.get(constants.CONFIG_RISK)
            or enums.ProfileRisk.MODERATE.value
        )
        self.profile_type = enums.ProfileType(
            profile_config.get(constants.CONFIG_TYPE)
            or enums.ProfileType.LIVE.value
        )
        self.extra_backtesting_time_frames = profile_config.get(
            constants.CONFIG_EXTRA_BACKTESTING_TIME_FRAMES, []
        )
        self.config = self.apply_default_values(profile_dict[constants.PROFILE_CONFIG])
        return self

    def save_config(self, global_config: dict):
        """
        Save this profile config
        :param global_config: the bot config containing profile data
        :return: None
        """
        for element in self.FULLY_MANAGED_ELEMENTS:
            if element in global_config:
                self.config[element] = copy.deepcopy(global_config[element])
        self.sync_partially_managed_elements(global_config)
        self._save_through_profile_storage(global_config)

    def remove_deleted_elements(self, global_config) -> bool:
        """
        Removes elements from self.PARTIALLY_MANAGED_ELEMENTS
        that are in profile but not in global config
        :return: True when any partially managed element key was removed
        """
        exchanges_changed = False
        for element in self.PARTIALLY_MANAGED_ELEMENTS:
            if element in global_config and element in self.config:
                current_elements = list(self.config[element])
                to_keep_elements = set(global_config[element])
                for key in current_elements:
                    if key not in to_keep_elements:
                        self.config[element].pop(key)
                        exchanges_changed = True
        return exchanges_changed

    def sync_partially_managed_elements(self, global_config):
        """
        Update the partially managed elements of this profile using the given configuration
        """
        for element in self.PARTIALLY_MANAGED_ELEMENTS:
            if element in global_config:
                allowed_keys = self.PARTIALLY_MANAGED_ELEMENTS_ALLOWED_KEYS.get(
                    element, None
                )
                if allowed_keys is not None:
                    self._filter_fill_elements(
                        global_config, self.config, element, allowed_keys
                    )

    def validate(self):
        """
        Validate this profile configuration against self.schema_path
        :return:
        """
        try:
            json_util.validate(self.as_dict(), self.schema_path)
        except FileNotFoundError as err:
            commons_logging.get_logger("ProfileSaver").warning(
                f"Impossible to validate profile: {err} ({err.__class__.__name__})"
            )

    def validate_and_save_config(self) -> None:
        """
        JSON validates this profile and then saves its configuration
        :return: None
        """
        self.validate()
        self._save_through_profile_storage(self._global_config_from_profile())

    def save(self) -> None:
        """
        Saves the current profile configuration
        :return: None
        """
        self.validate_and_save_config()

    def duplicate(self, name: str = None, description: str = None):
        """
        Duplicates the current profile and associates it with a new profile_id
        :param name: name of the profile to create, uses the original's one by default
        :param description: description of the profile to create, uses the original's one by default
        :return: the created profile
        """
        return self._require_profile_storage().duplicate_profile(self, name=name, description=description)

    def delete(self) -> None:
        self._require_profile_storage().delete_profile(self.profile_id, profile=self)

    def _save_through_profile_storage(self, global_config: dict) -> None:
        self._require_profile_storage().save_active_profile(self, global_config)

    def _global_config_from_profile(self) -> dict:
        global_config = {}
        for element in self.FULLY_MANAGED_ELEMENTS:
            global_config[element] = self.config.get(element, {})
        for element in self.PARTIALLY_MANAGED_ELEMENTS:
            if element in self.config:
                global_config[element] = self.config[element]
        return global_config

    def get_tentacles_config_path(self) -> str:
        """
        :return: The tentacles configurations path
        """
        return os.path.join(self.path, constants.CONFIG_TENTACLES_FILE)

    def init_tentacles_setup_config(self) -> None:
        setup = self._build_tentacles_setup_config()
        self.bind_tentacles_setup_config(setup)

    def bind_tentacles_setup_config(self, tentacles_setup_config):
        """
        Link profile and setup config both ways (setup.profile + profile.tentacles_setup_config).
        """
        tentacles_setup_config.profile = self
        self.tentacles_setup_config = tentacles_setup_config
        return tentacles_setup_config

    def get_tentacles_data(self) -> typing.Optional[list]:
        tentacles_setup_config = self.tentacles_setup_config
        if tentacles_setup_config is None:
            return None
        try:
            import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util
        except ImportError:
            return self._get_tentacles_data_without_tentacles_manager()
        return profile_tentacles_util.collect_tentacles_data_from_setup(
            tentacles_setup_config
        )

    def _get_tentacles_data_without_tentacles_manager(self) -> typing.Optional[list]:
        return None

    def _build_tentacles_setup_config(self):
        import octobot_commons.profiles.profile_data as profile_data_module
        import octobot_tentacles_manager.configuration.profile_tentacles_util as profile_tentacles_util

        writable_profile_path = self.get_writable_profile_path() if self._profile_storage else self.path
        os.makedirs(writable_profile_path, exist_ok=True)
        tentacles_config_path = self.get_tentacles_config_read_path()
        if os.path.isfile(tentacles_config_path):
            tentacles_setup_config = profile_tentacles_util.load_setup_config_from_profile_path(
                tentacles_config_path
            )
            tentacles_setup_config.config_path = tentacles_config_path
            return tentacles_setup_config
        try:
            profile_data = profile_data_module.ProfileData.from_filesystem_profile(self)
        except (KeyError, OSError, TypeError):
            profile_data = profile_data_module.ProfileData()
        return profile_tentacles_util.build_setup_config_from_profile_data(
            profile_data, writable_profile_path, import_registered_tentacles=True
        )

    def as_dict(self) -> dict:
        """
        :return: A dict representation of this profile configuration
        """
        return {
            constants.CONFIG_PROFILE: {
                constants.CONFIG_ID: self.profile_id,
                constants.CONFIG_NAME: self.name,
                constants.CONFIG_SLUG: self.slug,
                constants.CONFIG_DESCRIPTION: self.description,
                constants.CONFIG_AVATAR: self.avatar,
                constants.CONFIG_ORIGIN_URL: self.origin_url,
                constants.CONFIG_AUTO_UPDATE: self.auto_update,
                constants.CONFIG_READ_ONLY: self.read_only,
                constants.CONFIG_HIDDEN: self.hidden,
                constants.CONFIG_IMPORTED: self.imported,
                constants.CONFIG_COMPLEXITY: (
                    self.complexity.value if self.complexity else None
                ),
                constants.CONFIG_RISK: self.risk.value if self.risk else None,
                constants.CONFIG_TYPE: (
                    self.profile_type.value if self.profile_type else None
                ),
                constants.CONFIG_EXTRA_BACKTESTING_TIME_FRAMES: self.extra_backtesting_time_frames,
            },
            constants.PROFILE_CONFIG: self.config,
        }

    def merge_partially_managed_element_into_config(self, config: dict, element: str):
        """
        Merge this profile configuration's partially managed element into the given config
        :param config: dict to merge this profile configuration's partially managed element into
        :param element: the partially managed element to merge
        :return: None
        """
        Profile._merge_partially_managed_element(
            config, self.config, element, Profile.PARTIALLY_MANAGED_ELEMENTS[element]
        )

    @staticmethod
    def _merge_partially_managed_element(
        config: dict, profile_config: dict, element: str, template: dict
    ):
        if element in config:
            Profile._merge_profile_values(config, profile_config, element, template)
            Profile._apply_forced_default_values(config, profile_config, element)
        else:
            # use profile value for element
            config[element] = {
                key: Profile._get_element_from_template(template, val)
                for key, val in profile_config[element].items()
            }

    @staticmethod
    def _merge_profile_values(
        config: dict, profile_config: dict, element: str, template: dict
    ):
        for key, val in profile_config[element].items():
            if key in config[element]:
                if isinstance(config[element][key], dict):
                    # merge profile values for element[key]
                    Profile._merge_partially_managed_element(
                        config[element], profile_config[element], key, template
                    )
                else:
                    # overwrite element[key] by profile value
                    config[element][key] = copy.deepcopy(profile_config[element][key])
            else:
                # use profile value for element[key]
                if isinstance(val, dict):
                    config[element][key] = Profile._get_element_from_template(
                        template, val
                    )
                else:
                    config[element][key] = val

    @staticmethod
    def _apply_forced_default_values(config: dict, profile_config: dict, element: str):
        if element in Profile.PARTIALLY_MANAGED_ELEMENTS_FORCED_DEFAULT_KEYS:
            for config_key, config_val in config[element].items():
                if config_key not in profile_config[element]:
                    for config_sub_element in config_val:
                        if (
                            config_sub_element
                            in Profile.PARTIALLY_MANAGED_ELEMENTS_FORCED_DEFAULT_KEYS[
                                element
                            ]
                        ):
                            # item not in profile, it will be added to profile upon save
                            # use forced default profile value for forced default keys
                            config[element][config_key][config_sub_element] = (
                                Profile.PARTIALLY_MANAGED_ELEMENTS_FORCED_DEFAULT_KEYS[
                                    element
                                ][config_sub_element]
                            )

    @staticmethod
    def _get_element_from_template(template: dict, profile_values: dict) -> dict:
        merged_values = copy.deepcopy(template)
        merged_values.update(profile_values)
        return merged_values

    @staticmethod
    def _filter_fill_elements(
        config: dict, profile_config: dict, element: str, allowed_keys: list
    ):
        if element in config:
            # reset profile element to avoid saving outdated data
            profile_config[element] = {}
            for key, value in config[element].items():
                if isinstance(value, dict):
                    # handle nested elements
                    Profile._filter_fill_elements(
                        config[element], profile_config[element], key, allowed_keys
                    )
                else:
                    # save allowed keys
                    if key in allowed_keys:
                        profile_config[element][key] = value

    @staticmethod
    def apply_default_values(config: dict) -> dict:
        """
        Apply default values to the given config
        :param config: the config to apply default values to
        :return: the config with default values applied
        """
        if constants.CONFIG_DISTRIBUTION not in config:
            config[constants.CONFIG_DISTRIBUTION] = constants.DEFAULT_DISTRIBUTION
        return config
