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

import tools.tentacle_manager.tentacle_package_util as TentaclePackageUtil
import tools.tentacle_manager.tentacle_util as TentacleUtil
from tools.tentacle_manager.tentacle_package_manager import TentaclePackageManager

from config import TENTACLE_PACKAGE_DESCRIPTION, EVALUATOR_DEFAULT_FOLDER, CONFIG_TENTACLES_KEY, \
    TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION, TENTACLE_DESCRIPTION_IS_URL, EVALUATOR_ADVANCED_FOLDER, \
    TentacleManagerActions, TENTACLE_PACKAGE_NAME


class TentacleManager:

    TENTACLE_INSTALLATION_FOUND_MESSAGE = "Tentacles installation found on this OctoBot, this action will " \
                                          "replace every local tentacle file and their configuration by their " \
                                          "remote equivalent for the command's tentacles, continue ?"

    def __init__(self, config):
        self.config = config
        self.tentacle_package_manager = TentaclePackageManager(config, self)
        self.default_package = None
        self.advanced_package_list = []
        self.logger = get_logger(self.__class__.__name__)
        self.force_actions = False

    def install_tentacle_package(self, package_path_or_url, force=False):
        self.update_list()
        package = TentaclePackageUtil.get_package_description_with_adaptation(package_path_or_url)
        should_install = force
        if TentacleUtil.create_missing_tentacles_arch() and not force:
            should_install = self._confirm_action(self.TENTACLE_INSTALLATION_FOUND_MESSAGE)
        if should_install:
            self.tentacle_package_manager.set_max_steps(len(package) - 1)
            self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.INSTALL,
                                                                          package, EVALUATOR_ADVANCED_FOLDER)

    def parse_commands(self, commands, force=False):
        help_message = """- install: Install or re-install the given tentacles modules with their requirements if any.
    Also reset tentacles configuration files if any.
- update: Update the given tentacle modules with their requirements if any. Does not edit tentacles configuration files
- uninstall: Uninstall the given tentacle modules. Also delete the associated tentacle configuration.
- reset_tentacles: Deletes all the installed tentacle modules and configurations.
Note: install, update and uninstall commands can take 2 types of arguments:
    - all: applies the command to all available tentacles (remote and installed tentacles).
    - modules_name1, module_name2, ... : force to apply the command to the given tentacle modules 
          identified by their name and separated by a ' '."""
        self.update_list()
        if commands:
            if commands[0] == "install":
                if commands[1] == "all":
                    self.install_parser(commands, True, force=force)
                else:
                    commands.pop(0)
                    self.install_parser(commands, False, force=force)

            elif commands[0] == "update":
                if commands[1] == "all":
                    self.update_parser(commands, True)
                else:
                    commands.pop(0)
                    self.update_parser(commands, False)
                TentaclePackageManager.update_evaluator_config_file()
                TentaclePackageManager.update_trading_config_file()

            elif commands[0] == "uninstall":
                if self._confirm_action("Uninstall tentacle(s) and remove uninstalled tentacle(s) configuration ?"):
                    if commands[1] == "all":
                        self.uninstall_parser(commands, True)
                    else:
                        commands.pop(0)
                        self.uninstall_parser(commands, False)
                    TentaclePackageManager.update_evaluator_config_file()
                    TentaclePackageManager.update_trading_config_file()

            elif commands[0] == "reset_tentacles":
                if self._confirm_action("Reset ALL tentacles ? "
                                        "This will delete all tentacle files and configuration in tentacles folder."):
                    self.reset_tentacles()

            elif commands[0] in ["help", "h", "-h", "--help"]:
                self.logger.info(f"Welcome in Tentacle Manager, commands are:\n{help_message}")

            else:
                self.logger.error(f"Command not found: {commands[0]}, commands are:\n{help_message}")
        else:
            arguments_help = "-p: activates the package manager."
            self.logger.error(f"Invalid arguments, arguments are: {arguments_help}")

    def install_parser(self, commands, command_all=False, force=False):
        should_install = True
        # first ensure the current tentacles architecture is setup correctly
        if TentacleUtil.create_missing_tentacles_arch() and not force:
            should_install = self._confirm_action(self.TENTACLE_INSTALLATION_FOUND_MESSAGE)
        if should_install:
            # then process installations
            if command_all:

                self.tentacle_package_manager.set_max_steps(self._get_package_count())
                self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.INSTALL,
                                                                              self.default_package,
                                                                              EVALUATOR_DEFAULT_FOLDER)
                for package in self.advanced_package_list:
                    self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.INSTALL,
                                                                                  package, EVALUATOR_ADVANCED_FOLDER)

                nb_actions = self._get_package_count()
            else:
                nb_actions = len(commands)
                self.tentacle_package_manager.set_max_steps(nb_actions)
                for component in commands:

                    component = TentacleUtil.check_format(component)
                    package, _, localisation, is_url, destination, package_name = self.get_package_in_lists(component)

                    if package:
                        try:
                            self.tentacle_package_manager.process_module(TentacleManagerActions.INSTALL, package,
                                                                         component, localisation, is_url, destination,
                                                                         package_name)

                        except Exception as e:
                            self.logger.error(f"Installation failed for tentacle module '{component}'")
                            raise e
                    else:
                        self.logger.error(f"No installation found for tentacle module '{component}'")
                    self.tentacle_package_manager.inc_current_step()

            TentaclePackageManager.update_evaluator_config_file()
            TentaclePackageManager.update_trading_config_file()

            return nb_actions

    def update_parser(self, commands, command_all=False):
        self.tentacle_package_manager.set_installed_modules(self.tentacle_package_manager.get_installed_modules())
        if command_all:
            self.tentacle_package_manager.set_max_steps(self._get_package_count())
            self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.UPDATE,
                                                                          self.default_package,
                                                                          EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.UPDATE, package,
                                                                              EVALUATOR_ADVANCED_FOLDER)

            return self._get_package_count()

        else:
            nb_actions = len(commands)
            self.tentacle_package_manager.set_max_steps(nb_actions)
            for component in commands:

                component = TentacleUtil.check_format(component)
                package, _, localisation, is_url, destination, package_name = self.get_package_in_lists(component)

                if package:
                    try:
                        self.tentacle_package_manager.process_module(TentacleManagerActions.UPDATE, package, component,
                                                                     localisation, is_url, destination, package_name)

                    except Exception as e:
                        self.logger.error(f"Update failed for tentacle module '{component}'")
                        raise e
                else:
                    self.logger.error(f"No tentacle found for '{component}'")
                self.tentacle_package_manager.inc_current_step()

            return nb_actions

    def uninstall_parser(self, commands, command_all=False):
        if command_all:
            self.tentacle_package_manager.set_max_steps(self._get_package_count())
            self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.UNINSTALL,
                                                                          self.default_package,
                                                                          EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.UNINSTALL,
                                                                              package, EVALUATOR_ADVANCED_FOLDER)
            return self._get_package_count()
        else:
            nb_actions = len(commands)
            self.tentacle_package_manager.set_max_steps(nb_actions)
            for component in commands:

                component = TentacleUtil.check_format(component)
                package, _, _, _, destination, _ = self.get_package_in_lists(component)

                if package:
                    try:
                        self.tentacle_package_manager.process_module(TentacleManagerActions.UNINSTALL, package,
                                                                     component, "", "", destination, "")
                    except Exception:
                        self.logger.error(f"Uninstalling failed for module '{component}'")
                else:
                    self.logger.error(f"No module found for '{component}'")
                self.tentacle_package_manager.inc_current_step()
            return nb_actions

    def reset_tentacles(self):
        self.logger.info("Removing tentacles.")
        TentacleUtil.delete_tentacles_arch()
        TentacleUtil.create_missing_tentacles_arch()
        self.logger.info("Tentacles reset.")

    def update_list(self):
        default_package_list_url = TentaclePackageUtil.get_octobot_tentacle_public_repo()

        self.default_package = TentaclePackageUtil.get_package_description(default_package_list_url)

        if CONFIG_TENTACLES_KEY in self.config:
            for package in self.config[CONFIG_TENTACLES_KEY]:
                # try with package as in configuration
                try:
                    self.advanced_package_list.append(
                        TentaclePackageUtil.get_package_description_with_adaptation(package))
                except Exception:
                    self.logger.error(f"Impossible to get an OctoBot Tentacles Package at : {package}")

    def get_package_in_lists(self, component_name, component_version=None):
        if TentacleUtil.has_required_package(self.default_package, component_name, component_version):
            package_description = self.default_package[TENTACLE_PACKAGE_DESCRIPTION]
            package_localisation = package_description[TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION]
            is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
            package_name = package_description[TENTACLE_PACKAGE_NAME]
            return self.default_package, package_description, package_localisation, is_url, EVALUATOR_DEFAULT_FOLDER, \
                package_name
        else:
            for advanced_package in self.advanced_package_list:
                if TentacleUtil.has_required_package(advanced_package, component_name, component_version):
                    package_description = advanced_package[TENTACLE_PACKAGE_DESCRIPTION]
                    package_localisation = package_description[TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION]
                    url = package_description[TENTACLE_DESCRIPTION_IS_URL]
                    package_name = package_description[TENTACLE_PACKAGE_NAME]
                    return advanced_package, package_description, package_localisation, url, \
                        EVALUATOR_ADVANCED_FOLDER, package_name
        return None, None, None, None, None, None

    def _confirm_action(self, action):
        if self.force_actions:
            return True
        else:
            confirmation = ["yes", "ye", "y", "oui", "o"]
            user_input = input(f"{action} Y/N").lower()
            if user_input in confirmation:
                return True
            else:
                self.logger.info("Action aborted.")
                return False

    def set_force_actions(self, force_actions):
        self.force_actions = force_actions

    def _get_package_count(self):
        count = len(self.default_package)
        for advanced_package in self.advanced_package_list:
            count += len(advanced_package)
        # remove 1 for tentacle description for each tentacles package
        return count - 1*(1+len(self.advanced_package_list)) + 1
