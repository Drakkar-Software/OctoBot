import logging

import tools.tentacle_manager.tentacle_package_util as TentaclePackageUtil
import tools.tentacle_manager.tentacle_util as TentacleUtil
from tools.tentacle_manager.tentacle_package_manager import TentaclePackageManager

from config.cst import TENTACLE_PACKAGE_DESCRIPTION, EVALUATOR_DEFAULT_FOLDER, CONFIG_TENTACLES_KEY, \
    TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION, TENTACLE_DESCRIPTION_IS_URL, EVALUATOR_ADVANCED_FOLDER, \
    TentacleManagerActions,TENTACLE_PACKAGE_NAME


class TentacleManager:
    def __init__(self, config):
        self.config = config
        self.tentacle_package_manager = TentaclePackageManager(config, self)
        self.default_package = None
        self.advanced_package_list = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.force_actions = False

    def install_tentacle_package(self, package_path_or_url, force=False):
        self.update_list()
        package = TentaclePackageUtil.get_package_description_with_adaptation(package_path_or_url)
        should_install = force
        if TentacleUtil.create_missing_tentacles_arch() and not force:
            should_install = self._confirm_action("Tentacles installation found on this OctoBot, this action will "
                                                  "replace every local tentacle file and their configuration by their "
                                                  "remote equivalent for the command's tentacles, continue ?")
        if should_install:
            self.tentacle_package_manager.set_max_steps(len(package) - 1)
            self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.INSTALL,
                                                                          package, EVALUATOR_ADVANCED_FOLDER)

    def parse_commands(self, commands):
        help = "- install: Install or re-install the given tentacles modules with their requirements if any. " \
                                "Also reset tentacles configuration files if any.\n" \
                                "- update: Update the given tentacle modules with their requirements if any. " \
                                "Does not edit tentacles configuration files\n" \
                                "- uninstall: Uninstall the given tentacle modules. " \
                                "Also delete the tentacles configuration\n" \
                                "- reset_tentacles: Deletes all the installed tentacle modules and " \
                                "configuration.\n" \
                                "Note: install, update and uninstall commands can take 2 types of arguments: \n" \
                                "   - all: applies the command to all the available tentacles in remote and " \
                                "installed tentacles.\n" \
                                "   - modules_name1, module_name2, ... : force to apply the command to the given " \
                                "tentacle modules identified by their name and separated with a ' '."
        self.update_list()
        if commands:
            if commands[0] == "install":
                if commands[1] == "all":
                    self.install_parser(commands, True)
                else:
                    commands.pop(0)
                    self.install_parser(commands, False)

            elif commands[0] == "update":
                if commands[1] == "all":
                    self.update_parser(commands, True)
                else:
                    commands.pop(0)
                    self.update_parser(commands, False)
                TentaclePackageManager.update_evaluator_config_file()

            elif commands[0] == "uninstall":
                if self._confirm_action("Uninstall tentacle(s) and remove uninstalled tentacle(s) configuration ?"):
                    if commands[1] == "all":
                        self.uninstall_parser(commands, True)
                    else:
                        commands.pop(0)
                        self.uninstall_parser(commands, False)
                    TentaclePackageManager.update_evaluator_config_file()

            elif commands[0] == "reset_tentacles":
                if self._confirm_action("Reset ALL tentacles ? "
                                        "This will delete all tentacle files and configuration in tentacles folder."):
                    self.reset_tentacles()

            elif commands[0] == "help":
                self.logger.info("Welcome in Tentacle Manager, commands are:\n{0}".format(help))

            else:
                self.logger.error("Command not found: {0}, commands are:\n{1}".format(commands[0], help))
        else:
            arguments_help = "-p: activates the package manager."
            self.logger.error("Invalid arguments, arguments are: {0}".format(arguments_help))

    def install_parser(self, commands, command_all=False):
        should_install = True
        # first ensure the current tentacles architecture is setup correctly
        if TentacleUtil.create_missing_tentacles_arch():
            should_install = self._confirm_action("Tentacles installation found on this OctoBot, this action will "
                                                  "replace every local tentacle file and their configuration by their "
                                                  "remote equivalent for the command's tentacles, continue ?")
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
            else:
                self.tentacle_package_manager.set_max_steps(len(commands))
                for component in commands:

                    component = TentacleUtil.check_format(component)
                    package, _, localisation, is_url, destination, package_name = self.get_package_in_lists(component)

                    if package:
                        try:
                            self.tentacle_package_manager.process_module(TentacleManagerActions.INSTALL, package,
                                                                         component, localisation, is_url, destination,
                                                                         package_name)

                        except Exception as e:
                            self.logger.error("Installation failed for tentacle module '{0}'".format(component))
                            raise e
                    else:
                        self.logger.error("No installation found for tentacle module '{0}'".format(component))
                    self.tentacle_package_manager.inc_current_step()

            TentaclePackageManager.update_evaluator_config_file()

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

        else:
            self.tentacle_package_manager.set_max_steps(len(commands))
            for component in commands:

                component = TentacleUtil.check_format(component)
                package, _, localisation, is_url, destination, package_name = self.get_package_in_lists(component)

                if package:
                    try:
                        self.tentacle_package_manager.process_module(TentacleManagerActions.UPDATE, package, component,
                                                                     localisation, is_url, destination, package_name)

                    except Exception as e:
                        self.logger.error("Update failed for tentacle module '{0}'".format(component))
                        raise e
                else:
                    self.logger.error("No tentacle found for '{0}'".format(component))
                self.tentacle_package_manager.inc_current_step()

    def uninstall_parser(self, commands, command_all=False):
        if command_all:
            self.tentacle_package_manager.set_max_steps(self._get_package_count())
            self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.UNINSTALL,
                                                                          self.default_package,
                                                                          EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self.tentacle_package_manager.try_action_on_tentacles_package(TentacleManagerActions.UNINSTALL,
                                                                              package, EVALUATOR_ADVANCED_FOLDER)
        else:
            self.tentacle_package_manager.set_max_steps(len(commands))
            for component in commands:

                component = TentacleUtil.check_format(component)
                package, _, _, _, destination, _ = self.get_package_in_lists(component)

                if package:
                    try:
                        self.tentacle_package_manager.process_module(TentacleManagerActions.UNINSTALL, package,
                                                                     component, "", "", destination, "")
                    except Exception:
                        self.logger.error("Uninstalling failed for module '{0}'".format(component))
                else:
                    self.logger.error("No module found for '{0}'".format(component))
                self.tentacle_package_manager.inc_current_step()

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
                    self.logger.error("Impossible to get an OctoBot Tentacles Package at : {0}".format(package))

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
            user_input = input("{0} Y/N".format(action)).lower()
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
