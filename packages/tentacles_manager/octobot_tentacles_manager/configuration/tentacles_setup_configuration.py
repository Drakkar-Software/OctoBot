#  Drakkar-Software OctoBot-Tentacles-Manager
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
import os.path as path

import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants
import octobot_commons.profiles as commons_profiles

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.configuration as configuration
import octobot_tentacles_manager.loaders as loaders


class TentaclesSetupConfiguration:
    TENTACLE_ACTIVATION_KEY = "tentacle_activation"
    REGISTERED_TENTACLES_KEY = "registered_tentacles"
    INSTALLATION_CONTEXT_KEY = "installation_context"
    DEFAULT_DEACTIVATABLE_TENTACLE_SUB_TYPES = {
        constants.TENTACLES_EVALUATOR_REALTIME_PATH,
        constants.TENTACLES_EVALUATOR_TA_PATH,
        constants.TENTACLES_EVALUATOR_SCRIPTED_PATH,
        constants.TENTACLES_EVALUATOR_SOCIAL_PATH,
        constants.TENTACLES_EVALUATOR_STRATEGIES_PATH,
        constants.TENTACLES_TRADING_MODE_PATH,
        constants.TENTACLES_TRADING_SUPERVISOR_PATH,
    }

    def __init__(self, bot_installation_path=constants.DEFAULT_BOT_PATH,
                 config_path=constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.bot_installation_path = bot_installation_path
        self.config_path = path.join(bot_installation_path, config_path)
        self.tentacles_activation = {}
        self.registered_tentacles = {}
        self.installation_context = {}
        self.is_successfully_loaded = False

    def get_config_folder(self) -> str:
        return path.split(self.config_path)[0]

    def register_tentacles_package(self, package_name, package_location):
        self.registered_tentacles[package_name] = package_location

    def unregister_tentacles_package(self, package_name):
        self.registered_tentacles.pop(package_name)

    def get_installed_packages_from_url(self, url: str):
        return [
            package
            for package, package_url in self.registered_tentacles.items()
            if url == package_url
        ]

    def get_all_installed_package_urls(self):
        return list(set(
            url
            for url in self.registered_tentacles.values()
            if url != constants.UNKNOWN_TENTACLES_PACKAGE_LOCATION
        ))

    def fill_tentacle_config(self, tentacles, default_tentacle_config=constants.DEFAULT_TENTACLE_CONFIG,
                                   remove_missing_tentacles=True, update_location=None,
                                   force_update_registered_tentacles=False, newly_installed_tentacles=None,
                                   uninstalled_tentacles=None):
        self._update_tentacles_setup_config(tentacles,
                                            default_tentacle_config_file=default_tentacle_config,
                                            remove_missing_tentacles=remove_missing_tentacles,
                                            newly_installed_tentacles=newly_installed_tentacles,
                                            uninstalled_tentacles=uninstalled_tentacles)
        if update_location or force_update_registered_tentacles:
            self._update_registered_tentacles(tentacles, update_location)
        if not self.is_imported_profile(self.get_associated_profile_path()):
            self._fill_installation_context()

    def get_associated_profile_path(self):
        return os.path.split(self.config_path)[0]

    @staticmethod
    def is_imported_profile(profile_folder):
        try:
            return commons_profiles.Profile(profile_folder).read_config().imported
        except OSError:
            return False

    def refresh_profiles_tentacles_config(self,
                                          tentacles,
                                          profiles_path=commons_constants.USER_PROFILES_FOLDER,
                                          newly_installed_tentacles=None,
                                          uninstalled_tentacles=None
                                          ):
        bot_profiles_path = os.path.join(self.bot_installation_path, profiles_path)
        if not path.isdir(bot_profiles_path):
            return
        for profile_folder in os.scandir(bot_profiles_path):
            try:
                if profile_folder.is_dir():
                    self.refresh_profile_tentacles_config(tentacles, profile_folder,
                                                          newly_installed_tentacles, uninstalled_tentacles,
                                                          not self.is_imported_profile(profile_folder))
            except Exception as e:
                self.logger.exception(e, True, f"Unexpected error when patching profile tentacles version: {e}")

    def update_activation_configuration(self, new_config, deactivate_other_evaluators,
                                        add_missing_elements, tentacles_path=constants.TENTACLES_PATH):
        something_changed = False
        loaders.ensure_tentacles_metadata(tentacles_path)
        for element_name, activated in new_config.items():
            try:
                element_type = loaders.get_tentacle_classes()[element_name].tentacle_root_type
                if element_name in self.tentacles_activation[element_type]:
                    current_activation = self.tentacles_activation[element_type][element_name]
                    if current_activation != activated:
                        self.logger.info(f"Tentacles configuration updated: {element_name} "
                                         f"{'activated' if activated else 'deactivated'}")
                        self.tentacles_activation[element_type][element_name] = activated
                        something_changed = True
                elif add_missing_elements:
                    self.tentacles_activation[element_type][element_name] = activated
                    something_changed = True
            except KeyError:
                # tentacle missing in loaded metadata: can't be used
                self.logger.error(f"Impossible to change activation of {element_name}: this Tentacle class is not "
                                  f"in loaded tentacles metadata dict.")
        if deactivate_other_evaluators:
            something_changed = self._deactivate_other_evaluators(new_config) or something_changed
        return something_changed

    def is_tentacle_activated(self, tentacle_class_name, tentacles_path=constants.TENTACLES_PATH):
        loaders.ensure_tentacles_metadata(tentacles_path)
        tentacle_type = loaders.get_tentacle_classes()[tentacle_class_name].tentacle_root_type
        return self.tentacles_activation[tentacle_type][tentacle_class_name]

    def from_activated_tentacles_classes(self, *tentacles_classes, tentacles_path=constants.TENTACLES_PATH):
        loaders.ensure_tentacles_metadata(tentacles_path)
        tentacle_by_class_name = loaders.get_tentacle_classes()
        for tentacle_class in tentacles_classes:
            tentacle_name = tentacle_class if isinstance(tentacle_class, str) else tentacle_class.get_name()
            tentacle = tentacle_by_class_name[tentacle_name]
            try:
                self.tentacles_activation[tentacle.tentacle_root_type][tentacle_name] = True
            except KeyError:
                self.tentacles_activation[tentacle.tentacle_root_type] = {tentacle_name: True}

    def deactivate_all(self, trading_modes: bool, strategies: bool, evaluators: bool):
        to_deactivate_tentacles_types = [constants.TENTACLES_TRADING_MODE_PATH] if trading_modes else []
        to_deactivate_tentacles_types += [constants.TENTACLES_EVALUATOR_STRATEGIES_PATH] if strategies else []
        to_deactivate_tentacles_types += [
            constants.TENTACLES_EVALUATOR_TA_PATH,
            constants.TENTACLES_EVALUATOR_SOCIAL_PATH,
            constants.TENTACLES_EVALUATOR_REALTIME_PATH,
            constants.TENTACLES_EVALUATOR_SCRIPTED_PATH
        ] if evaluators else []
        for element_type, element_names in self.tentacles_activation.items():
            for element_name in element_names:
                try:
                    if loaders.get_tentacle_classes()[element_name].get_simple_tentacle_type() \
                            in to_deactivate_tentacles_types and self.tentacles_activation[element_type][element_name]:
                        self.logger.info(f"Tentacles configuration updated: {element_name} {'deactivated'}")
                        self.tentacles_activation[element_type][element_name] = False
                except KeyError:
                    # do not crash on missing tentacles
                    pass

    def _deactivate_other_evaluators(self, new_config):
        something_changed = False
        for element_type, element_names in self.tentacles_activation.items():
            for element_name in element_names:
                # for each activated element that is not in new_config
                if element_name not in new_config and self.tentacles_activation[element_type][element_name]:
                    # only handle evaluator tentacles
                    something_changed = self._deactivate_tentacle_if_evaluator(element_name, element_type) or \
                                        something_changed

        return something_changed

    def _deactivate_tentacle_if_evaluator(self, element_name, element_type):
        try:
            if loaders.get_tentacle_classes()[element_name].get_simple_tentacle_type() in {
                constants.TENTACLES_EVALUATOR_TA_PATH,
                constants.TENTACLES_EVALUATOR_SOCIAL_PATH,
                constants.TENTACLES_EVALUATOR_REALTIME_PATH,
                constants.TENTACLES_EVALUATOR_SCRIPTED_PATH
            }:
                self.logger.info(f"Tentacles configuration updated: {element_name} {'deactivated'}")
                self.tentacles_activation[element_type][element_name] = False
                return True
        except KeyError:
            # might happen when a tentacle is listed in config but has not been loaded in OctoBot (import fail etc)
            pass
        return False

    def _apply_default_profile_activation(self):
        default_profile = commons_profiles.Profile.load_profile(
            commons_constants.USER_PROFILES_FOLDER,
            commons_constants.DEFAULT_PROFILE
        )
        profile_setup_config = configuration.TentaclesSetupConfiguration(
            config_path=default_profile.get_tentacles_config_path()
        )
        # copy setup config from default profile
        self._from_dict(configuration.read_config(profile_setup_config.config_path), True)

    def _apply_reference_tentacles_config(self, read_activation_config):
        try:
            if read_activation_config:
                self._apply_default_profile_activation()
            else:
                self._from_dict(
                    configuration.read_config(constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH),
                    read_activation_config
                )
        except Exception as err:
            self.logger.exception(err, True, f"Error when applying reference config: {err}")
            # something really wrong happened
            raise

    def read_config(self, tentacles_path=constants.TENTACLES_PATH, read_activation_config=True):
        try:
            self._from_dict(configuration.read_config(self.config_path), read_activation_config)
        except Exception as e:
            self.logger.error(f"Error when reading tentacles global configuration file ({e}), "
                              "resetting this file with default values. This will not change "
                              "any tentacle configuration but will reset activated "
                              "trading modes and evaluators.")
            self._apply_reference_tentacles_config(read_activation_config)
            self.save_config()

    def save_config(self, is_config_update: bool = False) -> bool:
        changed = False
        parent_dir, _ = path.split(self.config_path)
        if not path.exists(parent_dir):
            os.makedirs(parent_dir)
        if not is_config_update or not configuration.is_same_config(self.config_path, self._to_dict()):
            configuration.write_config(self.config_path, self._to_dict())
            changed = True
        return changed

    def _update_tentacles_setup_config(self,
                                       tentacles,
                                       default_tentacle_config_file=constants.DEFAULT_TENTACLE_CONFIG,
                                       remove_missing_tentacles=True,
                                       newly_installed_tentacles=None,
                                       uninstalled_tentacles=None):
        default_config = configuration.read_config(default_tentacle_config_file)
        default_activation_config = default_config[self.TENTACLE_ACTIVATION_KEY] \
            if self.TENTACLE_ACTIVATION_KEY in default_config else {}
        for tentacle in tentacles:
            self._update_tentacle_activation(tentacle, default_activation_config)
        if remove_missing_tentacles:
            self._filter_tentacle_activation(tentacles)
        if newly_installed_tentacles or uninstalled_tentacles:
            self._update_tentacles_groups_activation(tentacles,
                                                     newly_installed_tentacles,
                                                     uninstalled_tentacles)

    def _update_tentacle_activation(self, tentacle, default_config):
        if tentacle.tentacle_root_type not in self.tentacles_activation:
            self.tentacles_activation[tentacle.tentacle_root_type] = {}
        for tentacle_class_name in tentacle.tentacle_class_names:
            if tentacle_class_name not in self.tentacles_activation[tentacle.tentacle_root_type]:
                self._set_activation_using_default_config(tentacle, tentacle_class_name, default_config)

    def _set_activation_using_default_config(self, tentacle, tentacle_class_name, default_config):
        if tentacle.tentacle_root_type in default_config:
            # if tentacle_type in default config: use default value or do not activate (unless
            # if tentacle sub type in DEFAULT_ACTIVATED_TENTACLE_TYPES)
            if tentacle_class_name in default_config[tentacle.tentacle_root_type]:
                self.tentacles_activation[tentacle.tentacle_root_type][tentacle_class_name] = \
                    default_config[tentacle.tentacle_root_type][tentacle_class_name]
                return

        # activate by default unless the sub type of this tentacle in among the sub types to be deactivated by default
        # or if tentacle_type not in default config: activate by default
        self.tentacles_activation[tentacle.tentacle_root_type][tentacle_class_name] = \
            tentacle.get_simple_tentacle_type() not in self.DEFAULT_DEACTIVATABLE_TENTACLE_SUB_TYPES

    def _filter_tentacle_activation(self, tentacles):
        tentacle_names = [tentacle_class_name
                          for tentacle in tentacles
                          for tentacle_class_name in tentacle.tentacle_class_names]
        for element_type, element_names in self.tentacles_activation.items():
            for element_name in list(element_names):
                if element_name not in tentacle_names:
                    self.tentacles_activation[element_type].pop(element_name)

    def _update_tentacles_groups_activation(self, tentacles, newly_installed_tentacles, uninstalled_tentacles):
        if newly_installed_tentacles:
            for new_tentacle in newly_installed_tentacles:
                if new_tentacle.get_simple_tentacle_type() not in self.DEFAULT_DEACTIVATABLE_TENTACLE_SUB_TYPES \
                        and new_tentacle.tentacle_group != new_tentacle.name:
                    # activate new_tentacle if part of tentacle to activate by default and has a tentacle group from
                    # which it's not the default tentacle: to avoid double tentacles: deactivate default one
                    self._update_default_tentacles_activation_for_group(tentacles, new_tentacle, False)
        if uninstalled_tentacles:
            for removed_tentacle in uninstalled_tentacles:
                if removed_tentacle.get_simple_tentacle_type() not in self.DEFAULT_DEACTIVATABLE_TENTACLE_SUB_TYPES \
                        and removed_tentacle.tentacle_group != removed_tentacle.name:
                    # re-activate default tentacle
                    self._update_default_tentacles_activation_for_group(tentacles, removed_tentacle, True)

    def _update_default_tentacles_activation_for_group(self, tentacles, updated_tentacle, activate):
        for tentacle in tentacles:
            if tentacle.tentacle_group == updated_tentacle.tentacle_group and tentacle.name != updated_tentacle.name:
                for tentacle_class_name in tentacle.tentacle_class_names:
                    self.tentacles_activation[tentacle.tentacle_root_type][tentacle_class_name] = activate

    def _update_registered_tentacles(self, tentacles, update_location):
        packages = set(tentacle.origin_package
                       for tentacle in tentacles)
        for package in packages:
            if package not in self.registered_tentacles:
                self.register_tentacles_package(package,
                                                update_location or constants.UNKNOWN_TENTACLES_PACKAGE_LOCATION)
        for registered_package in list(self.registered_tentacles):
            if registered_package not in packages:
                self.unregister_tentacles_package(registered_package)

    # Profiles management
    def refresh_profile_tentacles_config(self, tentacles, profile_folder,
                                         newly_installed_tentacles=None, uninstalled_tentacles=None,
                                         update_installation_context=True):
        self._refresh_profile_tentacles_config_file(tentacles,
                                                    path.join(profile_folder,
                                                              commons_constants.CONFIG_TENTACLES_FILE),
                                                    newly_installed_tentacles,
                                                    uninstalled_tentacles,
                                                    update_installation_context)

    def _refresh_profile_tentacles_config_file(self, tentacles, tentacles_config_file,
                                               newly_installed_tentacles, uninstalled_tentacles,
                                               update_installation_context):
        profile_setup_config = TentaclesSetupConfiguration(config_path=tentacles_config_file)
        profile_setup_config._from_dict(configuration.read_config(profile_setup_config.config_path), True)
        # use self.registered_tentacles as a reference
        profile_setup_config.registered_tentacles = self.registered_tentacles
        self._refresh_other_tentacles_activation_from_self(profile_setup_config)
        if update_installation_context:
            profile_setup_config._fill_installation_context()
        profile_setup_config._update_tentacles_groups_activation(tentacles,
                                                                 newly_installed_tentacles,
                                                                 uninstalled_tentacles)
        profile_setup_config.save_config()

    def _refresh_other_tentacles_activation_from_self(self, other):
        # add any missing element in tentacles activation
        for element_type, element_names in self.tentacles_activation.items():
            if element_type not in other.tentacles_activation:
                other.tentacles_activation[element_type] = {}
            for element_name in element_names:
                if element_name not in other.tentacles_activation[element_type]:
                    other.tentacles_activation[element_type][element_name] = \
                        self.tentacles_activation[element_type][element_name]
        # remove deleted tentacles activation
        for element_type, element_names in other.tentacles_activation.items():
            to_remove = []
            for element_name in element_names:
                try:
                    self.tentacles_activation[element_type][element_name]
                except KeyError:
                    to_remove.append(element_name)
            for element in to_remove:
                element_names.pop(element, None)

    def _ensure_installation_context(self):
        if not self.installation_context:
            self._fill_installation_context()

    def _fill_installation_context(self):
        self.installation_context[constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION] = \
                self._get_installation_context_bot_version()

    @staticmethod
    def _get_installation_context_bot_version() -> str:
        try:
            import octobot.constants as octobot_constants
            return octobot_constants.LONG_VERSION
        except ImportError:
            return constants.TENTACLE_INSTALLATION_CONTEXT_OCTOBOT_VERSION_UNKNOWN

    def _from_dict(self, input_dict, read_activation_config):
        if self.TENTACLE_ACTIVATION_KEY in input_dict:
            if read_activation_config:
                self.tentacles_activation = input_dict[self.TENTACLE_ACTIVATION_KEY]
            else:
                # only fill tentacle types to keep basic structure but do not include values
                for tentacle_type in input_dict[self.TENTACLE_ACTIVATION_KEY]:
                    self.tentacles_activation[tentacle_type] = {}
        if self.REGISTERED_TENTACLES_KEY in input_dict:
            self.registered_tentacles = input_dict[self.REGISTERED_TENTACLES_KEY]
        if self.INSTALLATION_CONTEXT_KEY in input_dict:
            self.installation_context = input_dict[self.INSTALLATION_CONTEXT_KEY]
            self._ensure_installation_context()
        self.is_successfully_loaded = bool(input_dict)

    def _to_dict(self):
        self._ensure_installation_context()
        return {
            self.TENTACLE_ACTIVATION_KEY: self.tentacles_activation,
            self.REGISTERED_TENTACLES_KEY: self.registered_tentacles,
            self.INSTALLATION_CONTEXT_KEY: self.installation_context,
        }
