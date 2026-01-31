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
import shutil

import octobot_commons.logging as logging

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.managers as managers
import octobot_tentacles_manager.util as util


class TentacleManager:

    def __init__(self, tentacle, bot_installation_path=constants.DEFAULT_BOT_PATH):
        self.tentacle = tentacle
        self.bot_installation_path = bot_installation_path
        self.target_tentacle_path = None

    async def install_tentacle(self, tentacle_path):
        self.target_tentacle_path = path.join(tentacle_path, self.tentacle.tentacle_type.to_path())
        tentacle_module_path = path.join(self.target_tentacle_path, self.tentacle.name)
        await self._update_tentacle_folder(tentacle_module_path)
        await managers.create_tentacle_init_file_if_necessary(tentacle_module_path, self.tentacle)

    async def uninstall_tentacle(self):
        shutil.rmtree(path.join(self.bot_installation_path, self.tentacle.tentacle_path, self.tentacle.name))

    @staticmethod
    def find_tentacles_missing_requirements(tentacle, to_install_version_by_modules, available_tentacles):
        # check if requirement is in tentacles to be installed in this call
        return {
            requirement: version
            for requirement, version in tentacle.extract_tentacle_requirements()
            if not TentacleManager.is_requirement_satisfied(requirement, version, tentacle,
                                                            to_install_version_by_modules, available_tentacles)
        }

    @staticmethod
    def is_requirement_satisfied(requirement, version, tentacle, to_install_version_by_modules, available_tentacles):
        satisfied = False
        # check in to install tentacles
        if requirement in to_install_version_by_modules:
            satisfied = TentacleManager._ensure_version(tentacle.name,
                                                        version,
                                                        to_install_version_by_modules[requirement])
        if not satisfied:
            # check in available tentacles
            for available_tentacle in available_tentacles:
                if available_tentacle.name == requirement:
                    return TentacleManager._ensure_version(tentacle.name,
                                                           version,
                                                           available_tentacle.version)
        return satisfied

    @staticmethod
    def _ensure_version(name, version, available_version):
        if version is None:
            return True
        elif version != available_version:
            logging.get_logger(TentacleManager.__name__). \
                error(f"Incompatible tentacle version requirement for "
                      f"{name}: requires {version}, installed: "
                      f"{available_version}. This tentacle might not work as expected")
            return True
        return False

    async def _update_tentacle_folder(self, target_tentacle_path):
        reference_tentacle_path = path.join(self.tentacle.tentacle_path, self.tentacle.name)
        await util.find_or_create(target_tentacle_path)
        for tentacle_file_entry in os.scandir(reference_tentacle_path):
            await util.replace_with_remove_or_rename(tentacle_file_entry,
                                                     path.join(target_tentacle_path, tentacle_file_entry.name))
