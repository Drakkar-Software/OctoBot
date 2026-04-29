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
import asyncio
import os
import os.path as path
import shutil

import octobot_commons.logging as logging

import octobot_tentacles_manager.configuration as configuration
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.managers as managers
import octobot_tentacles_manager.util as util


class TentaclesSetupManager:

    def __init__(self, tentacle_setup_root_path,
                 bot_installation_path=constants.DEFAULT_BOT_PATH,
                 default_tentacle_config=constants.DEFAULT_TENTACLE_CONFIG):
        self.tentacle_setup_root_path = tentacle_setup_root_path
        self.default_tentacle_config = default_tentacle_config
        self.bot_installation_path = bot_installation_path

    def refresh_user_tentacles_setup_config_file(self,
                                                 tentacles_setup_config_to_update=None,
                                                 update_location=None,
                                                 force_update_registered_tentacles=False,
                                                 newly_installed_tentacles=None,
                                                 uninstalled_tentacles=None):
        available_tentacle = util.load_tentacle_with_metadata(self.tentacle_setup_root_path)
        if not tentacles_setup_config_to_update:
            reference_tentacle_setup_config = configuration.TentaclesSetupConfiguration(
                bot_installation_path=self.bot_installation_path)
            # Do not read activation config to force default values generation and avoid side effects on
            # profiles activations
            reference_tentacle_setup_config.read_config(self.tentacle_setup_root_path, False)
        else:
            reference_tentacle_setup_config = tentacles_setup_config_to_update
        # fill overall tentacles setup config data
        reference_tentacle_setup_config.fill_tentacle_config(
            available_tentacle,
            self.default_tentacle_config,
            update_location=update_location,
            force_update_registered_tentacles=force_update_registered_tentacles,
            newly_installed_tentacles=newly_installed_tentacles,
            uninstalled_tentacles=uninstalled_tentacles
        )
        reference_tentacle_setup_config.save_config()
        # apply tentacles setup config data to each profile
        reference_tentacle_setup_config.refresh_profiles_tentacles_config(
            available_tentacle,
            newly_installed_tentacles=newly_installed_tentacles,
            uninstalled_tentacles=uninstalled_tentacles
        )

    def refresh_profile_tentacles_config(self, profile_folder):
        available_tentacle = util.load_tentacle_with_metadata(self.tentacle_setup_root_path)
        reference_tentacle_setup_config = configuration.TentaclesSetupConfiguration(
            bot_installation_path=self.bot_installation_path)
        # Do not read activation config to force default values generation and avoid side effects on
        # profiles activations
        reference_tentacle_setup_config.read_config(self.tentacle_setup_root_path, False)
        reference_tentacle_setup_config.fill_tentacle_config(
            available_tentacle,
            self.default_tentacle_config,
            remove_missing_tentacles=False,
            force_update_registered_tentacles=True
        )
        # apply tentacles setup config data to input profile
        reference_tentacle_setup_config.refresh_profile_tentacles_config(
            available_tentacle, profile_folder,
            update_installation_context=not reference_tentacle_setup_config.is_imported_profile(profile_folder)
        )

    async def create_missing_tentacles_arch(self):
        # tentacle user config folder
        await util.find_or_create(path.join(self.bot_installation_path, constants.USER_REFERENCE_TENTACLE_SPECIFIC_CONFIG_PATH))
        # tentacles folder
        found_existing_installation = not await util.find_or_create(self.tentacle_setup_root_path)
        # tentacle main python init file
        await util.find_or_create(path.join(self.tentacle_setup_root_path, constants.PYTHON_INIT_FILE), False,
                                  managers.get_module_init_file_content(constants.TENTACLES_FOLDERS_ARCH.keys()))
        # tentacle inner architecture
        await TentaclesSetupManager._tentacle_arch_operation(
            self.tentacle_setup_root_path,
            constants.TENTACLES_FOLDERS_ARCH,
            self._create_missing_files_and_folders,
            util.find_or_create_with_empty_init_file
        )
        await self._create_missing_files_and_folders(self.tentacle_setup_root_path, constants.TENTACLES_FOLDERS_ARCH)
        return found_existing_installation

    async def remove_tentacle_arch_init_files(self):
        await TentaclesSetupManager._remove_tentacles_arch_init_file(self.tentacle_setup_root_path, None)
        await TentaclesSetupManager._tentacle_arch_operation(self.tentacle_setup_root_path,
                                                             constants.TENTACLES_FOLDERS_ARCH,
                                                             self._remove_tentacles_arch_init_file,
                                                             self._remove_tentacles_arch_init_file)

    @staticmethod
    def cleanup_temp_dirs():
        if path.exists(constants.TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR):
            shutil.rmtree(constants.TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR)

    @staticmethod
    def is_tentacles_arch_valid(verbose=True, raises=False, import_tentacles=True) -> bool:
        try:
            if not TentaclesSetupManager._is_full_arch_valid(constants.TENTACLES_PATH,
                                                             constants.TENTACLES_FOLDERS_ARCH):
                return False
            if import_tentacles:
                import tentacles
            return True
        except (ImportError, SyntaxError) as e:
            if verbose:
                logging.get_logger(TentaclesSetupManager.__name__).exception(e, True,
                                                                             f"Error when importing tentacles: {e}")
            if raises:
                raise e
            return False

    @staticmethod
    def _is_full_arch_valid(root_folder, files_arch):
        for root, modules in files_arch.items():
            current_root = path.join(root_folder, root)
            if isinstance(modules, dict):
                if not TentaclesSetupManager._is_full_arch_valid(current_root, modules):
                    return False
            elif not all(path.exists(path.join(current_root, directory)) for directory in modules):
                return False
        return True

    @staticmethod
    def delete_tentacles_arch(
        force=False, raises=False, with_user_config=False, bot_installation_path=constants.DEFAULT_BOT_PATH,
        tentacles_folder_name=constants.TENTACLES_PATH
    ):
        if TentaclesSetupManager.is_tentacles_arch_valid(verbose=False, raises=raises) \
                or (force and path.exists(path.join(bot_installation_path, tentacles_folder_name))):
            shutil.rmtree(path.join(bot_installation_path, tentacles_folder_name))
        if with_user_config and path.exists(path.join(bot_installation_path, constants.USER_REFERENCE_TENTACLE_CONFIG_PATH)):
            shutil.rmtree(path.join(bot_installation_path, constants.USER_REFERENCE_TENTACLE_CONFIG_PATH))

    @staticmethod
    def get_available_tentacles_repos():
        # TODO: add advanced tentacles repos
        return [constants.TENTACLES_REQUIREMENTS_INSTALL_TEMP_DIR]

    @staticmethod
    async def _tentacle_arch_operation(root_folder, files_arch, branch_func, leaf_func):
        sub_dir_to_handle_coroutines = []
        for root, modules in files_arch.items():
            current_root = path.join(root_folder, root)
            await branch_func(current_root, modules)
            if isinstance(modules, dict):
                sub_dir_to_handle_coroutines.append(
                    TentaclesSetupManager._tentacle_arch_operation(current_root, modules, branch_func, leaf_func))
            elif leaf_func is not None:
                sub_dir_to_handle_coroutines += [leaf_func(path.join(current_root, directory))
                                                 for directory in modules]
        await asyncio.gather(*sub_dir_to_handle_coroutines)

    @staticmethod
    async def _create_missing_files_and_folders(current_root, modules):
        await util.find_or_create(current_root)
        # create python init file
        await managers.find_or_create_module_init_file(current_root, modules)

    @staticmethod
    async def _remove_tentacles_arch_init_file(current_root, _=None):
        potential_init_file = path.join(current_root, constants.PYTHON_INIT_FILE)
        if path.exists(potential_init_file):
            os.remove(potential_init_file)
