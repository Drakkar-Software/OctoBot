# pylint: disable=R0902, W0703
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
import copy
import os
import shutil
import uuid
import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.logging as commons_logging
import octobot_commons.json_util as json_util
import octobot_commons.errors as errors


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
        self.imported: bool = False
        self.complexity: enums.ProfileComplexity = enums.ProfileComplexity.MEDIUM
        self.risk: enums.ProfileRisk = enums.ProfileRisk.MODERATE
        self.profile_type: enums.ProfileType = enums.ProfileType.LIVE
        self.extra_backtesting_time_frames = []

        self.config: dict = {}

    def read_config(self):
        """
        Reads a profile from self.path
        :return: self
        """
        return self.from_dict(json_util.read_file(self.config_file()))

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
        self.imported = profile_config.get(constants.CONFIG_IMPORTED, False)
        self.complexity = enums.ProfileComplexity(
            profile_config.get(
                constants.CONFIG_COMPLEXITY, enums.ProfileComplexity.MEDIUM.value
            )
        )
        self.risk = enums.ProfileRisk(
            profile_config.get(constants.CONFIG_RISK, enums.ProfileRisk.MODERATE.value)
        )
        self.profile_type = enums.ProfileType(
            profile_config.get(constants.CONFIG_TYPE, enums.ProfileType.LIVE.value)
        )
        self.extra_backtesting_time_frames = profile_config.get(
            constants.CONFIG_EXTRA_BACKTESTING_TIME_FRAMES, []
        )
        self.config = self.apply_default_values(profile_dict[constants.PROFILE_CONFIG])
        if self.avatar and self.path:
            avatar_path = os.path.join(self.path, self.avatar)
            if os.path.isfile(avatar_path):
                self.avatar_path = avatar_path
        return self

    def save_config(self, global_config: dict):
        """
        Save this profile config
        :param global_config: the bot config containing profile data
        :return: None
        """
        for element in self.FULLY_MANAGED_ELEMENTS:
            if element in global_config:
                self.config[element] = global_config[element]
        self.sync_partially_managed_elements(global_config)
        self.validate_and_save_config()

    def remove_deleted_elements(self, global_config):
        """
        Removes elements from self.PARTIALLY_MANAGED_ELEMENTS
        that are in profile but not in global config
        """
        for element in self.PARTIALLY_MANAGED_ELEMENTS:
            if element in global_config and element in self.config:
                current_elements = list(self.config[element])
                to_keep_elements = set(global_config[element])
                for key in current_elements:
                    if key not in to_keep_elements:
                        self.config[element].pop(key)

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
        JSON validates this profile and then saves its configuration file
        :return: None
        """
        self.validate()
        self.save()

    def save(self) -> None:
        """
        Saves the current profile configuration file
        :return: None
        """
        json_util.safe_dump(self.as_dict(), self.config_file())

    def rename_folder(self, new_name, should_raise) -> str:
        """
        rename the profile folder
        :param new_name: name of the new folder
        :param should_raise: raises ProfileConflictError if the profile can't be renamed
        :return: the new profile path
        """
        new_path = os.path.join(os.path.split(self.path)[0], new_name)
        if os.path.exists(new_path):
            if should_raise:
                raise errors.ProfileConflictError(
                    "Skipping folder renaming: a profile already exists at this path"
                )
            return self.path
        try:
            os.rename(self.path, new_path)
            self.path = new_path
        except Exception as err:
            commons_logging.get_logger("ProfileRenamer").error(
                f"Error when renaming profile: {err}"
            )
            raise errors.ProfileConflictError from err
        return self.path

    def duplicate(self, name: str = None, description: str = None):
        """
        Duplicates the current profile and associates it with a new profile_id
        :param name: name of the profile to create, uses the original's one by default
        :param description: description of the profile to create, uses the original's one by default
        :return: the created profile
        """
        clone = copy.deepcopy(self)
        clone.name = name or clone.name
        clone.description = description or clone.description
        clone.profile_id = str(uuid.uuid4())
        clone.read_only = False
        clone.imported = False
        clone.origin_url = None
        clone.auto_update = False
        try:
            clone.path = os.path.join(
                os.path.split(self.path)[0], f"{clone.name}_{clone.profile_id}"
            )
            shutil.copytree(self.path, clone.path)
        except OSError:
            # invalid profile name for a filename
            clone.path = os.path.join(os.path.split(self.path)[0], clone.profile_id)
            shutil.copytree(self.path, clone.path)
        clone.save()
        return clone

    def get_tentacles_config_path(self) -> str:
        """
        :return: The tentacles configurations path
        """
        return os.path.join(self.path, constants.CONFIG_TENTACLES_FILE)

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

    def config_file(self):
        """
        :return: the path to this profile config file
        """
        return os.path.join(self.path, constants.PROFILE_CONFIG_FILE)

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
    def load_profile(profiles_path, profile_id, schema_path: str = None):
        """
        :param profiles_path: the path to look for the profile
        :param profile_id: the required profile id
        :return: the loaded profile
        """
        for profile in Profile.get_all_profiles(profiles_path, schema_path=schema_path):
            if profile.profile_id == profile_id:
                return profile
        raise errors.NoProfileError(f"No profile with id: {profile_id}")

    @staticmethod
    def get_all_profiles(profiles_path, ignore: str = None, schema_path: str = None):
        """
        Loads profiles found in the given directory
        :param profiles_path: Path to a directory containing profiles
        :param ignore: A profile path to ignore
        :param schema_path: Path to the json schema to pass to the created profile instances
        :return: the profile instances list
        """
        profiles = []
        ignored_path = None if ignore is None else os.path.normpath(ignore)
        for profile_entry in os.scandir(profiles_path):
            if (
                ignored_path is None
                or os.path.normpath(profile_entry.path) != ignored_path
            ):
                profile = Profile._load_profile(profile_entry.path, schema_path)
                if profile is not None:
                    profiles.append(profile)
        return profiles

    @staticmethod
    def _load_profile(profile_path: str, schema_path: str):
        logger = commons_logging.get_logger("ProfileExplorer")
        profile = Profile(profile_path, schema_path)
        try:
            if os.path.isfile(profile.config_file()):
                profile.read_config()
                return profile
            logger.debug(
                f"Ignored {profile_path} as it does not contain a profile configuration"
            )
        except Exception as err:
            logger.exception(
                err,
                True,
                f"Ignored profile due to an error upon reading '{profile_path}': {err}",
            )
        return None

    @staticmethod
    def get_all_profiles_ids(profiles_path, ignore: str = None):
        """
        Get ids of profiles found in the given directory
        :param profiles_path: Path to a directory containing profiles
        :param ignore: A profile path to ignore in ids listing
        :return: the profile ids list
        """
        return [
            profile.profile_id
            for profile in Profile.get_all_profiles(profiles_path, ignore)
        ]

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
