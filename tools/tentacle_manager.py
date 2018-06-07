import json
import logging
import os
from enum import Enum

import requests

from config.cst import TENTACLES_PUBLIC_LIST, TENTACLES_DEFAULT_BRANCH, TENTACLES_PUBLIC_REPOSITORY, \
    TENTACLE_DESCRIPTION, GITHUB_RAW_CONTENT_URL, EVALUATOR_DEFAULT_FOLDER, CONFIG_TENTACLES_KEY, GITHUB_BASE_URL, \
    GITHUB, TENTACLE_DESCRIPTION_LOCALISATION, TENTACLE_DESCRIPTION_IS_URL, EVALUATOR_ADVANCED_FOLDER, TENTACLE_TYPES, \
    EVALUATOR_CONFIG_FOLDER, TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR, TENTACLE_MODULE_NAME, \
    TENTACLE_MODULE_TYPE, TENTACLE_MODULE_SUBTYPE, TENTACLE_MODULE_VERSION, TENTACLE_MODULE_CONFIG_FILES, \
    TENTACLE_MODULE_REQUIREMENTS


class TentacleManager:
    def __init__(self, config):
        self.config = config
        self.default_package = None
        self.advanced_package_list = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.just_processed_packages = []

    def update_list(self):
        default_package_list_url = "{0}/{1}/{2}/{3}".format(GITHUB_BASE_URL,
                                                            TENTACLES_PUBLIC_REPOSITORY,
                                                            TENTACLES_DEFAULT_BRANCH,
                                                            TENTACLES_PUBLIC_LIST)

        self.default_package = self._get_package_description(default_package_list_url)

        if CONFIG_TENTACLES_KEY in self.config:
            for package in self.config[CONFIG_TENTACLES_KEY]:
                # try with package as in configuration
                try:
                    self.advanced_package_list.append(self._get_package_description(package))
                except Exception:
                    try:
                        self.advanced_package_list.append(self._get_package_description(package, True))
                    except Exception:
                        self.logger.error("Impossible to get a OctoBot Tentacle at : {0}".format(package))

    @staticmethod
    def _add_package_description_metadata(package_description, localisation, is_url):
        to_save_loc = str(localisation)
        if localisation.endswith(TENTACLES_PUBLIC_LIST):
            to_save_loc = localisation[0:-len(TENTACLES_PUBLIC_LIST)]
            while to_save_loc.endswith("/") or to_save_loc.endswith("\\"):
                to_save_loc = to_save_loc[0:-1]
        package_description[TENTACLE_DESCRIPTION] = {
            TENTACLE_DESCRIPTION_LOCALISATION: to_save_loc,
            TENTACLE_DESCRIPTION_IS_URL: is_url
        }

    def _get_package_in_lists(self, component):
        if component in self.default_package:
            package_description = self.default_package[TENTACLE_DESCRIPTION]
            package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
            is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
            return self.default_package, package_description, package_localisation, is_url, EVALUATOR_DEFAULT_FOLDER
        else:
            for advanced_package in self.advanced_package_list:
                if component in advanced_package:
                    package_description = advanced_package[TENTACLE_DESCRIPTION]
                    package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
                    url = package_description[TENTACLE_DESCRIPTION_IS_URL]
                    return advanced_package, package_description, package_localisation, url, EVALUATOR_ADVANCED_FOLDER
        return None, None, None, None, None

    @staticmethod
    def _get_package_description(url_or_path, try_to_adapt=False):
        package_url_or_path = str(url_or_path)
        # if its an url: download with requests.get and return text
        if package_url_or_path.startswith("https://") \
                or package_url_or_path.startswith("http://") \
                or package_url_or_path.startswith("ftp://"):
            if try_to_adapt:
                if not package_url_or_path.endswith("/"):
                    package_url_or_path += "/"
                # if checking on github, try adding branch and file
                if GITHUB in package_url_or_path:
                    package_url_or_path += "{0}/{1}".format(TENTACLES_DEFAULT_BRANCH, TENTACLES_PUBLIC_LIST)
                # else try adding file
                else:
                    package_url_or_path += TENTACLES_PUBLIC_LIST
            downloaded_result = json.loads(requests.get(package_url_or_path).text)
            if "error" in downloaded_result and GITHUB_BASE_URL in package_url_or_path:
                package_url_or_path = package_url_or_path.replace(GITHUB_BASE_URL, GITHUB_RAW_CONTENT_URL)
                downloaded_result = json.loads(requests.get(package_url_or_path).text)
            # add package metadata
            TentacleManager._add_package_description_metadata(downloaded_result, package_url_or_path, True)
            return downloaded_result

        # if its a local path: return file content
        else:
            if try_to_adapt:
                if not package_url_or_path.endswith("/"):
                    package_url_or_path += "/"
                package_url_or_path += TENTACLES_PUBLIC_LIST
            with open(package_url_or_path, "r") as package_description:
                read_result = json.loads(package_description.read())
                # add package metadata
                TentacleManager._add_package_description_metadata(read_result, package_url_or_path, False)
                return read_result

    @staticmethod
    def _get_package_from_url(url):
        package_file = requests.get(url).text

        if package_file.find("404: Not Found") != -1:
            raise Exception(package_file)

        return package_file

    @staticmethod
    def _create_localization_from_type(localization, module_type, module_subtype, file):
        # create path from types
        if module_subtype:
            return "{0}/{1}/{2}/{3}".format(localization,
                                            module_type,
                                            module_subtype,
                                            file)
        else:
            return "{0}/{1}/{2}".format(localization,
                                        module_type,
                                        file)

    @staticmethod
    def _create_path_from_type(module_type, module_subtype, target_folder):
        # create path from types
        if module_subtype:
            return "{0}/{1}/{2}".format(TENTACLE_TYPES[module_type],
                                        TENTACLE_TYPES[module_subtype],
                                        target_folder)
        else:
            return "{0}/{1}".format(TENTACLE_TYPES[module_type],
                                    target_folder)

    @staticmethod
    def _parse_module(package, module_name):
        return {
            TENTACLE_MODULE_NAME: package[module_name][TENTACLE_MODULE_NAME],
            TENTACLE_MODULE_TYPE: package[module_name][TENTACLE_MODULE_TYPE],
            TENTACLE_MODULE_SUBTYPE: package[module_name][TENTACLE_MODULE_SUBTYPE]
            if TENTACLE_MODULE_SUBTYPE in package[module_name] else None,
            TENTACLE_MODULE_VERSION: package[module_name][TENTACLE_MODULE_VERSION],
            TENTACLE_MODULE_REQUIREMENTS: package[module_name][TENTACLE_MODULE_REQUIREMENTS]
            if TENTACLE_MODULE_REQUIREMENTS in package[module_name] else None,
            TENTACLE_MODULE_CONFIG_FILES: package[module_name][TENTACLE_MODULE_CONFIG_FILES]
            if TENTACLE_MODULE_CONFIG_FILES in package[module_name] else None,
        }

    def _apply_module(self, action, module_type, module_subtype,
                      module_version, module_file, target_folder, module_name):

        if module_subtype in TENTACLE_TYPES and (module_subtype or module_subtype in TENTACLE_TYPES):

            file_dir = self._create_path_from_type(module_type, module_subtype, target_folder)

            package_file_path = "{0}/{1}.py".format(file_dir, module_name)

            # Write the new file in locations
            if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                # Install package in evaluator
                with open(package_file_path, "w") as installed_package:
                    installed_package.write(module_file)

            # remove package line from init file
            elif action == TentacleManagerActions.UNINSTALL:
                try:
                    os.remove(package_file_path)
                except OSError:
                    pass

            # Update local __init__
            line_in_init = "from .{0} import *\n".format(module_name)
            init_content = ""
            init_file = "{0}/{1}/{2}/__init__.py".format(TENTACLE_TYPES[module_type],
                                                         TENTACLE_TYPES[module_subtype],
                                                         target_folder)

            if os.path.isfile(init_file):
                with open(init_file, "r") as init_file_r:
                    init_content = init_file_r.read()

            # check if line already exists
            line_exists = False if init_content.find(line_in_init) == -1 else True

            # Add new package in init file
            if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                if not line_exists:
                    with open(init_file, "w") as init_file_w:
                        # add new package to init
                        init_file_w.write(init_content + line_in_init)

            # remove package line from init file
            elif action == TentacleManagerActions.UNINSTALL:
                if line_exists:
                    with open(init_file, "w") as init_file_w:
                        # remove package to uninstall from init
                        init_file_w.write(init_content.replace(line_in_init, ""))

            if action == TentacleManagerActions.INSTALL:
                self.logger.info("{0} {1} successfully installed in: {2}"
                                 .format(module_name, module_version, file_dir))
            elif action == TentacleManagerActions.UNINSTALL:
                self.logger.info("{0} {1} successfully uninstalled in: {2}"
                                 .format(module_name, module_version, file_dir))
            elif action == TentacleManagerActions.UPDATE:
                self.logger.info("{0} {1} successfully updated in: {2}"
                                 .format(module_name, module_version, file_dir))

        else:
            raise Exception("Tentacle type not found")

    def process_module(self, action, package, module_name, package_localisation, is_url, target_folder):
        parsed_module = self._parse_module(package, module_name)
        package_type = parsed_module[TENTACLE_MODULE_TYPE]
        package_subtype = parsed_module[TENTACLE_MODULE_SUBTYPE]
        module_file = ""

        if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
            module_loc = "{0}.py".format(self._create_localization_from_type(package_localisation,
                                                                             package_type,
                                                                             package_subtype,
                                                                             module_name))

            if is_url:
                module_file = self._get_package_from_url(module_loc)
            else:
                with open(module_loc, "r") as module:
                    module_file = module.read()

        # manage module config
        self._try_action_on_config(action, package, module_name, is_url, package_localisation)

        self._apply_module(action, package_type, package_subtype, parsed_module[TENTACLE_MODULE_VERSION],
                           module_file, target_folder, module_name)

        if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
            self._try_action_on_requirements(action, package, module_name)

    def _try_action_on_package(self, action, package, target_folder):
        package_description = package[TENTACLE_DESCRIPTION]
        package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
        is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
        for module in package:
            try:
                if module != TENTACLE_DESCRIPTION:
                    self.process_module(action, package, module, package_localisation, is_url, target_folder)
            except Exception as e:
                error = "failed for module '{0}' ({1})".format(module, e)
                if action == TentacleManagerActions.INSTALL:
                    self.logger.error("Installation {0}".format(error))
                elif action == TentacleManagerActions.UNINSTALL:
                    self.logger.error("Uninstalling {0}".format(error))
                elif action == TentacleManagerActions.UPDATE:
                    self.logger.error("Updating {0}".format(error))

    def _try_action_on_requirements(self, action, package, module_name):
        parsed_module = self._parse_module(package, module_name)
        success = True
        module_name = parsed_module[TENTACLE_MODULE_NAME]
        applied_modules = [module_name]
        if parsed_module[TENTACLE_MODULE_REQUIREMENTS]:
            for requirement in parsed_module[TENTACLE_MODULE_REQUIREMENTS]:
                try:
                    req_package, description, localisation, is_url, destination = self._get_package_in_lists(
                        requirement)

                    if req_package:
                        self.process_module(action, req_package, requirement, localisation, is_url, destination)
                        applied_modules.append(requirement)
                    else:
                        raise Exception("Module requirement '{0}' not found in package lists".format(requirement))

                except Exception as e:
                    error = "failed for module requirement '{0}' of module {1} ({2})".format(requirement, module_name,
                                                                                             e)
                    if action == TentacleManagerActions.INSTALL:
                        self.logger.error("Installation {0}".format(error))
                    elif action == TentacleManagerActions.UNINSTALL:
                        self.logger.error("Uninstalling {0}".format(error))
                    elif action == TentacleManagerActions.UPDATE:
                        self.logger.error("Updating {0}".format(error))
                    success = False

            # failed to install requirements
            if not success:
                # uninstall module and requirements
                #  TODO : rollback to previous version (for UPDATE action)
                for module in applied_modules:
                    req_package, description, localisation, is_url, destination = self._get_package_in_lists(module)
                    if req_package:
                        self.process_module(TentacleManagerActions.UNINSTALL, req_package, module,
                                            localisation, is_url, destination)

    def _try_action_on_config(self, action, package, module_name, is_url, package_localisation):
        parsed_module = self._parse_module(package, module_name)

        if parsed_module[TENTACLE_MODULE_CONFIG_FILES]:
            for config_file in parsed_module[TENTACLE_MODULE_CONFIG_FILES]:

                file_dir = self._create_path_from_type(parsed_module[TENTACLE_MODULE_TYPE],
                                                       parsed_module[TENTACLE_MODULE_SUBTYPE], "")

                config_file_path = "{0}{1}/{2}".format(file_dir, EVALUATOR_CONFIG_FOLDER, config_file)
                if action == TentacleManagerActions.INSTALL:

                    try:
                        # get config file content from localization
                        module_loc = self._create_localization_from_type(package_localisation,
                                                                         parsed_module[TENTACLE_MODULE_TYPE],
                                                                         parsed_module[TENTACLE_MODULE_SUBTYPE],
                                                                         config_file)

                        if is_url:
                            config_file_content = self._get_package_from_url(module_loc)
                        else:
                            with open(module_loc, "r") as module:
                                config_file_content = module.read()

                        # install local config file content
                        with open(config_file_path, "w") as new_config_file:
                            new_config_file.write(config_file_content)

                    except Exception as e:
                        raise Exception("Fail to install configuration".format(e))

                elif action == TentacleManagerActions.UNINSTALL:
                    try:
                        os.remove(config_file_path)
                    except OSError:
                        pass
                elif action == TentacleManagerActions.UPDATE:
                    # TODO warning about erasing file
                    pass

    @staticmethod
    def parse_version(version):
        return [int(value) for value in version.split(".")]

    @staticmethod
    def parse_requirements(requirement):
        requirement_info = requirement.split(TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR)
        return {TENTACLE_MODULE_NAME: requirement_info[0],
                TENTACLE_MODULE_VERSION: requirement_info[1] if len(requirement_info) > 1 else None}

    def parse_commands(self, commands):
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

            elif commands[0] == "uninstall":
                if commands[1] == "all":
                    self.uninstall_parser(commands, True)
                else:
                    commands.pop(0)
                    self.uninstall_parser(commands, False)

            else:
                self.logger.error("Command not found")
        else:
            self.logger.error("Invalid arguments")

    def install_parser(self, commands, command_all=False):
        if command_all:
            self._try_action_on_package(TentacleManagerActions.INSTALL, self.default_package, EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self._try_action_on_package(TentacleManagerActions.INSTALL, package, EVALUATOR_ADVANCED_FOLDER)
        else:
            for component in commands:

                package, description, localisation, is_url, destination = self._get_package_in_lists(component)

                if package:
                    try:
                        self.process_module(TentacleManagerActions.INSTALL, package, component,
                                            localisation, is_url, destination)

                    except Exception as e:
                        self.logger.error("Installation failed for module '{0}'".format(component))
                        raise e
                else:
                    self.logger.error("No installation found for module '{0}'".format(component))

    def update_parser(self, commands, command_all=False):
        if command_all:
            # TODO check for each tentacle installed if update is available (with requirements)
            pass
        else:
            # TODO check for each tentacle specified if update is available (with requirements)
            pass

    def uninstall_parser(self, commands, command_all=False):
        if command_all:
            self._try_action_on_package(TentacleManagerActions.UNINSTALL, self.default_package,
                                        EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self._try_action_on_package(TentacleManagerActions.UNINSTALL, package, EVALUATOR_ADVANCED_FOLDER)
        else:
            for component in commands:
                try:
                    self.process_module(TentacleManagerActions.UNINSTALL, self.default_package,
                                        component, "", "", EVALUATOR_DEFAULT_FOLDER)
                except Exception:
                    self.logger.error("Uninstalling failed for module '{0}'".format(component))


class TentacleManagerActions(Enum):
    INSTALL = 1
    UNINSTALL = 2
    UPDATE = 3
