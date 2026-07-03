# pylint: disable=R0913, R0902, W0703
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
import os
import functools
import copy
import typing

import octobot_commons.logging as logging
import octobot_commons.errors as errors
import octobot_commons.constants as commons_constants
import octobot_commons.profiles as profiles
import octobot_commons.profiles.profile_storage as profile_storage_module
import octobot_commons.json_util as json_util
import octobot_commons.configuration.config_file_manager as config_file_manager
import octobot_commons.configuration.config_operations as config_operations


class Configuration:
    """
    Configuration is managing an OctoBot configuration regarding reading, writing and updating
    """

    def __init__(
        self,
        config_path: str,
        profiles_path: str,
        schema_path: str = None,
        profile_schema_path: str = None,
    ):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.config_path: str = config_path
        self.profiles_path: str = profiles_path
        self.config: dict = None
        self.config_schema_path: str = (
            schema_path or commons_constants.CONFIG_FILE_SCHEMA
        )
        self.profile_schema_path: str = (
            profile_schema_path or commons_constants.PROFILE_FILE_SCHEMA
        )

        self._read_config: dict = None
        self.profile: profiles.Profile = None
        self.profile_by_id: dict = {}
        self.profile_storage = profile_storage_module.ProfileStorage(
            profiles_path,
            profile_schema_path,
        )

    def validate(self) -> None:
        """
        Validated self._read_config and self._profile against their json schema
        :return: None
        """
        json_util.validate(self._read_config, self.config_schema_path)
        self.profile.validate()

    def read(
        self,
        should_raise=True,
        fill_missing_fields=False,
        *,
        activate_profile=True,
    ) -> None:
        """
        Reads the configuration from self.config_path and load the current profile
        Overall config is stored into self.config and consists of a merger from the user
        config and activated profile
        :param should_raise: will raise upon exception when True
        :param fill_missing_fields: will try to fill in missing fields when true
        :param activate_profile: when False, only load config.json without selecting a profile
        :return: None
        """
        self._read_config = config_file_manager.load(
            self.config_path,
            should_raise=should_raise,
            fill_missing_fields=fill_missing_fields,
        )
        self.config = copy.deepcopy(self._read_config)
        if activate_profile:
            self.load_profiles_if_possible_and_necessary()

    def activate_saved_profile(self) -> None:
        """
        Load all profiles and select CONFIG_PROFILE from the last read config.json.
        """
        self.load_profiles_if_possible_and_necessary()

    def load_profiles_if_possible_and_necessary(self) -> None:
        """
        Loads profiles if profiles already exists and have not been already loaded
        :return: None
        """
        if not self.are_profiles_empty_or_missing() and not self.are_profile_loaded():
            self.load_profiles()
            self.select_profile(self._get_selected_profile())

    def select_profile(self, profile_id) -> None:
        """
        Sets self.profile using its profile_id
        :param profile_id: id of the profile to select
        :return: None
        """
        self.config[commons_constants.CONFIG_PROFILE] = profile_id
        self.profile = self.profile_by_id[profile_id]
        self.profile_storage.activate_profile(self.profile)
        self.logger.info(f"Using {self.profile.name} profile.")
        self._generate_config_from_user_config_and_profile()

    def remove_profile(self, profile_id: str) -> None:
        """
        Removes the given profile and deletes its folder on disk
        :param profile_id: the id of the profile to remove
        :return: None
        """
        profile = self.profile_by_id[profile_id]
        if profile.read_only and not profile.imported:
            raise errors.ProfileRemovalError(f"{profile.name} profile can't be removed")
        try:
            self.profile_storage.delete_profile(
                profile_id,
                profile=profile,
            )
            self.profile_by_id.pop(profile_id, None)
        except errors.ProfileRemovalError:
            raise
        except Exception as err:
            raise errors.ProfileRemovalError() from err

    def _generate_config_from_user_config_and_profile(self):
        for profile_managed_element in self.profile.FULLY_MANAGED_ELEMENTS:
            self.config[profile_managed_element] = copy.deepcopy(
                self.profile.config[profile_managed_element]
            )
        for partially_managed_element in self.profile.PARTIALLY_MANAGED_ELEMENTS:
            self.profile.merge_partially_managed_element_into_config(
                self.config, partially_managed_element
            )

    def save(
        self,
        schema_file=None,
        sync_all_profiles: bool = False,
        save_profile: typing.Optional[bool] = None,
    ) -> None:
        """
        Save the current self.config and self.profile.
        Synchronize all profiles if sync_all_profiles
        :return: None
        """
        config_to_save = self._get_config_without_profile_elements()
        config_file_manager.dump(
            self.config_path,
            config_to_save,
            schema_file=schema_file,
        )
        if save_profile is None:
            save_profile = self._profile_managed_elements_changed()
        if (
            save_profile
            and self.profile is not None
            and not self.profile_storage.is_master_overlay_profile(self.profile)
        ):
            self.profile.save_config(self.config)
        if sync_all_profiles:
            self._sync_other_profiles()

    def _profile_managed_elements_changed(self) -> bool:
        if self.profile is None:
            return False
        for element in self.profile.FULLY_MANAGED_ELEMENTS:
            if element in self.config:
                if self.config[element] != self.profile.config.get(element):
                    return True
        for element in self.profile.PARTIALLY_MANAGED_ELEMENTS:
            if self._partially_managed_element_would_change(element):
                return True
        return False

    def _partially_managed_element_would_change(self, element: str) -> bool:
        if element not in self.config:
            return False
        allowed_keys = profiles.Profile.PARTIALLY_MANAGED_ELEMENTS_ALLOWED_KEYS.get(
            element
        )
        if allowed_keys is None:
            return self.config[element] != self.profile.config.get(element)
        global_element = self.config[element]
        profile_element = self.profile.config.get(element, {})
        for exchange_name, global_exchange_config in global_element.items():
            if not isinstance(global_exchange_config, dict):
                continue
            profile_exchange_config = profile_element.get(exchange_name, {})
            if not isinstance(profile_exchange_config, dict):
                return True
            for allowed_key in allowed_keys:
                if global_exchange_config.get(allowed_key) != profile_exchange_config.get(
                    allowed_key
                ):
                    return True
        return False

    def _sync_other_profiles(self):
        """
        Update profile partially managed elements for all profiles except self.profile
        with self.config
        """
        for profile in self.profile_by_id.values():
            if profile is self.profile:
                # do not synchronize self.profile
                continue
            try:
                profile.remove_deleted_elements(self.config)
                profile.validate_and_save_config()
            except Exception as err:
                self.logger.exception(
                    f"Error when synchronizing '{profile.name}' profile at '{profile.path}': {err}",
                    False,
                    err,
                )

    def is_loaded(self) -> bool:
        """
        Checks if self has been loaded
        :return: True when self has been loaded (read)
        """
        return self.config is not None

    def is_config_file_empty_or_missing(self) -> bool:
        """
        Checks if self.config_path existing and not empty
        :return: True when self.config_path is existing and non empty
        """
        return (not os.path.isfile(self.config_path)) or os.stat(
            self.config_path
        ).st_size == 0

    def are_profile_loaded(self) -> bool:
        """
        Checks if profiles have already been loaded
        :return: True if profiles have been loaded
        """
        return self.profile is not None

    def are_profiles_empty_or_missing(self) -> bool:
        """
        Checks if self.profiles_path exists and contains folders
        :return: True if profiles folder is not empty
        """
        self._prepare_profile_storage()
        return not (
            self.profile_storage.has_any_profiles()
            or (
                os.path.isdir(self.profiles_path) and os.listdir(self.profiles_path)
            )
        )

    def get_non_imported_profiles(self) -> list:
        """
        :return: The list of loaded profiles in self that have not been imported into this OctoBot
        """
        return [
            profile for profile in self.profile_by_id.values() if not profile.imported
        ]

    def get_tentacles_config_path(self) -> str:
        """
        :return: The tentacles configurations associated to the activated profile
        """
        return self.profile.get_tentacles_config_path()

    def get_active_tentacles_setup_config(self):
        """
        :return: The tentacles setup config for the activated profile.
        Profile-data-backed profiles use in-memory setup; filesystem profiles use their config path.
        """
        if self.profile.is_profile_data_tentacle_backed():
            if self.profile.tentacles_setup_config is None:
                self.profile.init_tentacles_setup_config()
            tentacles_setup_config = self.profile.tentacles_setup_config
            return self.profile.bind_tentacles_setup_config(tentacles_setup_config)
        import octobot_tentacles_manager.api as tentacles_manager_api

        return tentacles_manager_api.get_tentacles_setup_config(
            self.get_tentacles_config_path(),
            profile=self.profile,
        )

    def get_metrics_enabled(self) -> bool:
        """
        Check if metrics are enabled
        :return: True if metrics are enabled
        """
        return bool(
            self.config.get(commons_constants.CONFIG_METRICS, {}).get(
                commons_constants.CONFIG_ENABLED_OPTION, True
            )
        )

    def get_metrics_id(self) -> str:
        """
        :return: The current user's metrics id
        """
        return self.config[commons_constants.CONFIG_METRICS][
            commons_constants.CONFIG_METRICS_BOT_ID
        ]

    def accepted_terms(self) -> bool:
        """
        Check if terms has been accepted
        :return: the check result
        """
        return self.config.get(commons_constants.CONFIG_ACCEPTED_TERMS, False)

    def accept_terms(self, accepted) -> None:
        """
        Perform terms acceptation
        :param accepted: accepted or not
        """
        self.config[commons_constants.CONFIG_ACCEPTED_TERMS] = accepted
        self.save()

    def update_config_fields(
        self,
        to_update_fields,
        in_backtesting,
        config_separator,
        delete=False,
    ) -> None:
        """
        Partially update self.config using the fields found in to_update_fields
        :param to_update_fields: the fields to update
        :param in_backtesting: if backtesting is enabled
        :param config_separator: the config separator
        :param delete: if the data should be removed
        """
        config_operations.filter_to_update_data(to_update_fields, in_backtesting)
        removed_configs = []
        if delete:
            removed_configs = [
                config_operations.parse_and_update(
                    data_key, config_operations.DELETE_ELEMENT_VALUE, config_separator
                )
                for data_key in to_update_fields
            ]
            functools.reduce(
                config_operations.clear_dictionaries_by_keys,
                [self.config] + removed_configs,
            )
        else:
            updated_configs = [
                config_operations.parse_and_update(
                    data_key, data_value, config_separator
                )
                for data_key, data_value in to_update_fields.items()
            ]
            # merge configs
            functools.reduce(
                config_operations.merge_dictionaries_by_appending_keys,
                [self.config] + updated_configs,
            )
        # ensure encrypted fields
        config_file_manager.encrypt_values_if_necessary(self.config)

        # save config
        self.save(
            schema_file=self.config_schema_path, sync_all_profiles=bool(removed_configs)
        )

    def _get_selected_profile(self):
        selected_profile_id = self._read_config.get(
            commons_constants.CONFIG_PROFILE, commons_constants.DEFAULT_PROFILE
        )
        if selected_profile_id in self.profile_by_id:
            return selected_profile_id
        if (
            selected_profile_id != commons_constants.DEFAULT_PROFILE
            and commons_constants.DEFAULT_PROFILE in self.profile_by_id
        ):
            self.logger.warning(
                "Profile %r from config.json is not available yet; falling back to %r. "
                "This can happen when sync profiles are not loaded.",
                selected_profile_id,
                commons_constants.DEFAULT_PROFILE,
            )
            return commons_constants.DEFAULT_PROFILE
        raise errors.NoProfileError

    def _prepare_profile_storage(self) -> None:
        self.profile_storage.configure_paths(
            self.profiles_path, self.profile_schema_path
        )
        if self.config:
            readonly_profiles_path = self.config.get(
                commons_constants.CONFIG_READONLY_PROFILES_PATH
            )
            if readonly_profiles_path:
                self.profile_storage.configure_readonly_profiles_path(
                    readonly_profiles_path
                )

    def load_profiles(self) -> None:
        """
        Loads the available profiles
        :return: None
        """
        self._prepare_profile_storage()
        loaded_profiles = self.profile_storage.load_all_profiles()
        for profile_id, profile in loaded_profiles.items():
            if profile_id not in self.profile_by_id:
                self.profile_by_id[profile_id] = profile

    def refresh_sync_profiles(self) -> None:
        """
        Reload sync-backed profiles from storage into profile_by_id.
        Used when the sync collection may have changed externally.
        """
        if not self.profile_storage.is_sync_available():
            return
        self._prepare_profile_storage()
        loaded_sync_profiles = self.profile_storage.list_sync_profiles()
        loaded_sync_profile_ids = set(loaded_sync_profiles)
        for profile_id, profile in loaded_sync_profiles.items():
            self.profile_by_id[profile_id] = profile
        removed_sync_profile_ids = [
            profile_id
            for profile_id, profile in list(self.profile_by_id.items())
            if profile.is_sync_backed() and profile_id not in loaded_sync_profile_ids
        ]
        for profile_id in removed_sync_profile_ids:
            self.profile_by_id.pop(profile_id, None)
        if self.profile is not None and self.profile.is_sync_backed():
            refreshed_profile = self.profile_by_id.get(self.profile.profile_id)
            if refreshed_profile is not None:
                self.profile = refreshed_profile

    def _get_config_without_profile_elements(self) -> dict:
        filtered_config = copy.deepcopy(self.config)
        # do not include profile fully managed elements into filtered config
        for profile_managed_element in profiles.Profile.FULLY_MANAGED_ELEMENTS:
            filtered_config.pop(profile_managed_element, None)
        return filtered_config

    def dev_mode_enabled(self) -> bool:
        """
        Check if DEV_MODE is enabled
        :return: bool
        """
        return commons_constants.IS_DEV_MODE_ENABLED or self.config.get(
            commons_constants.CONFIG_DEBUG_OPTION, False
        )
