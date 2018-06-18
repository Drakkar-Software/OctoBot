import logging
import os
import shutil
import copy
import json
from enum import Enum

import requests

from config.cst import TENTACLES_PUBLIC_LIST, TENTACLES_DEFAULT_BRANCH, TENTACLES_PUBLIC_REPOSITORY, \
    TENTACLE_DESCRIPTION, GITHUB_RAW_CONTENT_URL, EVALUATOR_DEFAULT_FOLDER, CONFIG_TENTACLES_KEY, GITHUB_BASE_URL, \
    GITHUB, TENTACLE_DESCRIPTION_LOCALISATION, TENTACLE_DESCRIPTION_IS_URL, EVALUATOR_ADVANCED_FOLDER, TENTACLE_TYPES, \
    EVALUATOR_CONFIG_FOLDER, TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR, TENTACLE_MODULE_NAME, \
    TENTACLE_MODULE_TYPE, TENTACLE_MODULE_SUBTYPE, TENTACLE_MODULE_VERSION, TENTACLE_MODULE_CONFIG_FILES, \
    TENTACLE_MODULE_REQUIREMENTS, TENTACLE_MODULE_LIST_SEPARATOR, TENTACLE_MODULE_REQUIREMENT_WITH_VERSION, \
    TENTACLE_MODULE_DESCRIPTION, TENTACLES_INSTALL_FOLDERS, TENTACLES_PATH, TENTACLES_EVALUATOR_PATH, \
    TENTACLES_TRADING_PATH, TENTACLES_EVALUATOR_REALTIME_PATH, TENTACLES_EVALUATOR_TA_PATH, \
    TENTACLES_EVALUATOR_SOCIAL_PATH, TENTACLES_EVALUATOR_STRATEGIES_PATH, TENTACLES_EVALUATOR_UTIL_PATH, \
    TENTACLES_TRADING_MODE_PATH, TENTACLES_PYTHON_INIT_CONTENT, PYTHON_INIT_FILE, CONFIG_EVALUATOR_FILE_PATH, \
    CONFIG_DEFAULT_EVALUATOR_FILE, TENTACLE_MODULE_TESTS, TENTACLES_TEST_PATH


class TentacleManager:
    def __init__(self, config):
        self.config = config
        self.default_package = None
        self.advanced_package_list = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.just_processed_modules = []
        self.installed_modules = {}

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
                        self.logger.error("Impossible to get an OctoBot Tentacles Package at : {0}".format(package))

    def _get_package_in_lists(self, component_name, component_version=None):
        if self._has_required_package(self.default_package, component_name, component_version):
            package_description = self.default_package[TENTACLE_DESCRIPTION]
            package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
            is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
            return self.default_package, package_description, package_localisation, is_url, EVALUATOR_DEFAULT_FOLDER
        else:
            for advanced_package in self.advanced_package_list:
                if self._has_required_package(advanced_package, component_name, component_version):
                    package_description = advanced_package[TENTACLE_DESCRIPTION]
                    package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
                    url = package_description[TENTACLE_DESCRIPTION_IS_URL]
                    return advanced_package, package_description, package_localisation, url, EVALUATOR_ADVANCED_FOLDER
        return None, None, None, None, None

    def _apply_module(self, action, module_type, module_subtype,
                      module_version, module_file, module_test_files, target_folder, module_name):

        if module_subtype in TENTACLE_TYPES and (module_subtype or module_subtype in TENTACLE_TYPES):

            # Update module file
            file_dir = self._create_path_from_type(module_type, module_subtype, target_folder)

            package_file_path = "{0}/{1}.py".format(file_dir, module_name)

            # Write the new file in locations
            if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                # Install package in evaluator
                with open(package_file_path, "w") as installed_package:
                    installed_package.write(module_file)

            # Remove package line from init file
            elif action == TentacleManagerActions.UNINSTALL:
                try:
                    os.remove(package_file_path)
                except OSError:
                    pass

            # Update local __init__
            line_in_init = "from .{0} import *\n".format(module_name)
            init_file = "{0}/{1}/{2}/{3}/{4}".format(TENTACLES_PATH,
                                                     TENTACLE_TYPES[module_type],
                                                     TENTACLE_TYPES[module_subtype],
                                                     target_folder,
                                                     PYTHON_INIT_FILE)

            self._update_init_file(action, init_file, line_in_init)

            # Update module test files
            test_file_dir = self._create_path_from_type(module_type, module_subtype, target_folder, True)
            for test_file, test_file_content in module_test_files.items():
                package_test_file_path = "{0}/{1}.py".format(test_file_dir, test_file)

                # Write the new file in locations
                if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                    # Install package in evaluator
                    with open(package_test_file_path, "w") as installed_package_test:
                        installed_package_test.write(test_file_content)

                # Remove package line from init file
                elif action == TentacleManagerActions.UNINSTALL:
                    try:
                        os.remove(package_test_file_path)
                    except OSError:
                        pass

            if action == TentacleManagerActions.INSTALL:
                self.logger.info("{0} {1} successfully installed in: {2}"
                                 .format(module_name, module_version, file_dir))
            elif action == TentacleManagerActions.UNINSTALL:
                self.logger.info("{0} {1} successfully uninstalled (file: {2})"
                                 .format(module_name, module_version, file_dir))
            elif action == TentacleManagerActions.UPDATE:
                self.logger.info("{0} successfully updated to version {1} in: {2}"
                                 .format(module_name, module_version, file_dir))
            self.just_processed_modules.append(TentacleManager._get_full_module_identifier(module_name, module_version))

        else:
            raise Exception("Tentacle type not found")

    def process_module(self, action, package, module_name, package_localisation, is_url, target_folder):
        parsed_module = self._parse_module(package[module_name])
        package_type = parsed_module[TENTACLE_MODULE_TYPE]
        package_subtype = parsed_module[TENTACLE_MODULE_SUBTYPE]
        package_tests = parsed_module[TENTACLE_MODULE_TESTS]
        module_file = ""
        module_test_files = {test: "" for test in package_tests} if package_tests else {}

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

            if module_test_files:
                for test in package_tests:
                    test_loc = "{0}.py".format(self._create_localization_from_type(package_localisation,
                                                                                   package_type,
                                                                                   package_subtype,
                                                                                   test,
                                                                                   True))

                    if is_url:
                        module_test_files[test] = self._get_package_from_url(test_loc)
                    else:
                        with open(test_loc, "r") as module:
                            module_test_files[test] = module.read()

        # manage module config
        self._try_action_on_config(action, package, module_name, is_url, package_localisation)

        self._apply_module(action, package_type, package_subtype, parsed_module[TENTACLE_MODULE_VERSION],
                           module_file, module_test_files, target_folder, module_name)

        if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
            self._try_action_on_requirements(action, package, module_name)

    def _should_do_something(self, action, module_name, module_version, need_this_exact_version=False, requiring=None):
        if action == TentacleManagerActions.UPDATE:
            if self._is_module_in_list(module_name, None, self.installed_modules):
                installed_version = self.installed_modules[module_name][TENTACLE_MODULE_VERSION]
                if not need_this_exact_version:
                    new_version_available = TentacleManager._is_first_version_superior(module_version, installed_version)
                    if not new_version_available:
                        self.logger.info("{0} version {1} is already up to date".format(module_name, installed_version))
                    return new_version_available
                else:
                    is_required_version_installed = True
                    print_version = "any version"
                    if module_version is not None:
                        is_required_version_installed = installed_version == module_version
                        print_version = "version {0}".format(module_version)
                    if is_required_version_installed:
                        self.logger.info("{0} dependency: {1} {2} is satisfied."
                                         .format(requiring, module_name, print_version))
                        return False
                    else:
                        return True
            else:
                if requiring:
                    self.logger.error("can't find module: {0} required for {1} in installed Tentacles. "
                                      "Try to install the required Tentacle".format(module_name, requiring))
                else:
                    self.logger.info("new module found in Tentacles: {0}. "
                                     "You can install it using the command: {1}"
                                     .format(module_name, "start.py -p install {0}".format(module_name)))

            return False
        else:
            return True

    def _try_action_on_package(self, action, package, target_folder):
        package_description = package[TENTACLE_DESCRIPTION]
        package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
        is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
        for module in package:
            try:
                if module != TENTACLE_DESCRIPTION and \
                        not self._has_just_processed_module(module, package[module][TENTACLE_MODULE_VERSION]) and \
                        self._should_do_something(action, module, package[module][TENTACLE_MODULE_VERSION]):
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
        parsed_module = self._parse_module(package[module_name])
        success = True
        module_name = parsed_module[TENTACLE_MODULE_NAME]
        applied_modules = [module_name]
        if parsed_module[TENTACLE_MODULE_REQUIREMENTS]:
            for requirement_data in parsed_module[TENTACLE_MODULE_REQUIREMENTS]:
                if success:
                    requirement_module_name = requirement_data[TENTACLE_MODULE_NAME]
                    requirement_module_version = requirement_data[TENTACLE_MODULE_VERSION]
                    if not self._has_just_processed_module(requirement_module_name, requirement_module_version) and \
                            self._should_do_something(action, requirement_module_name,
                                                      requirement_module_version, True, module_name):
                        try:
                            req_package, _, localisation, is_url, destination = self._get_package_in_lists(
                                requirement_module_name, requirement_module_version)

                            if req_package:
                                self.process_module(action, req_package, requirement_module_name,
                                                    localisation, is_url, destination)
                                applied_modules.append(requirement_module_name)
                            else:
                                raise Exception("module requirement '{0}' not found in package lists"
                                                .format(requirement_data[TENTACLE_MODULE_REQUIREMENT_WITH_VERSION]))

                        except Exception as e:
                            error = "failed for module requirement '{0}' of module {1} ({2})"\
                                .format(requirement_module_name, module_name, e)
                            if action == TentacleManagerActions.INSTALL:
                                self.logger.error("installation {0}".format(error))
                            elif action == TentacleManagerActions.UNINSTALL:
                                self.logger.error("uninstalling {0}".format(error))
                            elif action == TentacleManagerActions.UPDATE:
                                self.logger.error("updating {0}".format(error))
                            success = False

            # failed to install requirements
            if not success:
                if action == TentacleManagerActions.UPDATE:
                    # uninstall module
                    # TODO : rollback to previous version
                    req_package, _, localisation, is_url, destination = self._get_package_in_lists(module_name)
                    if req_package:
                        self.process_module(TentacleManagerActions.UNINSTALL, req_package, module_name,
                                            localisation, is_url, destination)

                elif action == TentacleManagerActions.INSTALL:
                    # uninstall module and requirements
                    for module in applied_modules:
                        req_package, _, localisation, is_url, destination = self._get_package_in_lists(module)
                        if req_package:
                            self.process_module(TentacleManagerActions.UNINSTALL, req_package, module,
                                                localisation, is_url, destination)

    def _try_action_on_config(self, action, package, module_name, is_url, package_localisation):
        parsed_module = self._parse_module(package[module_name])

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
                        raise Exception("Fail to install configuration : {}".format(e))

                elif action == TentacleManagerActions.UNINSTALL:
                    try:
                        os.remove(config_file_path)
                    except OSError:
                        pass
                elif action == TentacleManagerActions.UPDATE:
                    self.logger.info("{0} configuration file for {1} module ignored to save the current "
                                     "configuration. Re-install this module if you want to restore the default "
                                     "configuration.".format(config_file, module_name))

    def _has_just_processed_module(self, module_name, module_version):
        return self._is_module_in_list(module_name, module_version, self.just_processed_modules)

    def _init_installed_modules(self):
        # Foreach folder (not hidden)
        for root_dir in os.listdir(os.getcwd()):
            if os.path.isdir(root_dir) and not root_dir.startswith('.'):
                TentacleManager._read_tentacles(root_dir, self.installed_modules)

    def parse_commands(self, commands):
        help = "- install: Install or re-install the given modules with their requirements if any. " \
                                "Also reset modules configuration files if any.\n" \
                                "- update: Update the given tentacles with their requirements if any. " \
                                "Does not edit modules configuration files\n" \
                                "- uninstall: Uninstall the given modules. " \
                                "Also delete the module configuration\n" \
                                "- reset_tentacles: Deletes all the installed tentacles, their modules and " \
                                "configuration.\n" \
                                "Note: install, update and uninstall commands can take 2 types of arguments: \n" \
                                "   - all: applies the command to all the available modules in remote and " \
                                "installed tentacles.\n" \
                                "   - modules_name1, module_name2, ... : force to apply the command to the given " \
                                "modules identified by their name and separated with a ' '."
        self.update_list()
        if commands:
            if commands[0] == "install":
                if commands[1] == "all":
                    self.install_parser(commands, True)
                else:
                    commands.pop(0)
                    self.install_parser(commands, False)
                self._update_evaluator_config_file()

            elif commands[0] == "update":
                if commands[1] == "all":
                    self.update_parser(commands, True)
                else:
                    commands.pop(0)
                    self.update_parser(commands, False)
                self._update_evaluator_config_file()

            elif commands[0] == "uninstall":
                if commands[1] == "all":
                    self.uninstall_parser(commands, True)
                else:
                    commands.pop(0)
                    self.uninstall_parser(commands, False)
                self._update_evaluator_config_file()

            elif commands[0] == "reset_tentacles":
                self.reset_tentacles()

            elif commands[0] == "help":
                self.logger.info("Welcome in Tentacle Manager, commands are:\n{0}".format(help))

            else:
                self.logger.error("Command not found, commands are:\n{0}".format(help))
        else:
            arguments_help = "-p: activates the package manager."
            self.logger.error("Invalid arguments, arguments are: {0}".format(arguments_help))

    def install_parser(self, commands, command_all=False):
        # first ensure the current tentacles architecture is setup correctly
        self._create_missing_tentacles_arch()

        # then process installations
        if command_all:
            self._try_action_on_package(TentacleManagerActions.INSTALL, self.default_package, EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self._try_action_on_package(TentacleManagerActions.INSTALL, package, EVALUATOR_ADVANCED_FOLDER)
        else:
            for component in commands:

                component = self._check_format(component)
                package, _, localisation, is_url, destination = self._get_package_in_lists(component)

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
        self._init_installed_modules()
        if command_all:
            self._try_action_on_package(TentacleManagerActions.UPDATE, self.default_package, EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self._try_action_on_package(TentacleManagerActions.UPDATE, package, EVALUATOR_ADVANCED_FOLDER)

        else:
            for component in commands:

                component = self._check_format(component)
                package, _, localisation, is_url, destination = self._get_package_in_lists(component)

                if package:
                    try:
                        self.process_module(TentacleManagerActions.UPDATE, package, component,
                                            localisation, is_url, destination)

                    except Exception as e:
                        self.logger.error("Update failed for module '{0}'".format(component))
                        raise e
                else:
                    self.logger.error("No module found for '{0}'".format(component))

    def uninstall_parser(self, commands, command_all=False):
        if command_all:
            self._try_action_on_package(TentacleManagerActions.UNINSTALL, self.default_package,
                                        EVALUATOR_DEFAULT_FOLDER)
            for package in self.advanced_package_list:
                self._try_action_on_package(TentacleManagerActions.UNINSTALL, package, EVALUATOR_ADVANCED_FOLDER)
        else:
            for component in commands:

                component = self._check_format(component)
                package, _, _, _, destination = self._get_package_in_lists(component)

                if package:
                    try:
                        self.process_module(TentacleManagerActions.UNINSTALL, package,
                                            component, "", "", destination)
                    except Exception:
                        self.logger.error("Uninstalling failed for module '{0}'".format(component))
                else:
                    self.logger.error("No module found for '{0}'".format(component))

    def reset_tentacles(self):
        self.logger.info("Removing tentacles.")
        self._delete_tentacles_arch()
        self._create_missing_tentacles_arch()
        self.logger.info("Tentacles reset.")

    @staticmethod
    def _delete_tentacles_arch():
        if os.path.exists(TENTACLES_PATH):
            shutil.rmtree(TENTACLES_PATH)

    @staticmethod
    def _create_missing_tentacles_arch():
        tentacle_architecture, tentacle_extremity_architecture = TentacleManager._get_tentacles_arch()
        for tentacle_root, subdir in tentacle_architecture.items():
            TentacleManager._find_or_create(tentacle_root)
            for tentacle_dir in subdir:
                for tentacle_type_dir, types_subdir in tentacle_dir.items():
                    type_path = os.path.join(tentacle_root, tentacle_type_dir)
                    TentacleManager._find_or_create(type_path)
                    if isinstance(types_subdir, dict):
                        for tentacle_subtype_dir, types_subsubdir in types_subdir.items():
                            test_type_path = os.path.join(type_path, tentacle_subtype_dir)
                            TentacleManager._find_or_create(test_type_path)
                            TentacleManager._create_arch_module_extremity(tentacle_extremity_architecture,
                                                                          types_subsubdir, test_type_path, False)
                    else:
                        TentacleManager._create_arch_module_extremity(tentacle_extremity_architecture,
                                                                      types_subdir, type_path)

    @staticmethod
    def _create_arch_module_extremity(architecture, types_subdir, type_path, with_init_and_config=True):
        for module_type in types_subdir:
            path = os.path.join(type_path, module_type)
            TentacleManager._find_or_create(path)
            for extremity_folder in architecture:
                module_content_path = os.path.join(path, extremity_folder)
                # add Advanced etc folders
                TentacleManager._find_or_create(module_content_path)
            init_path = os.path.join(path, PYTHON_INIT_FILE)
            # add init.py file
            if with_init_and_config:
                module_config_path = os.path.join(path, EVALUATOR_CONFIG_FOLDER)
                TentacleManager._find_or_create(module_config_path)
                TentacleManager._find_or_create(init_path, False)

    @staticmethod
    def _find_or_create(path, is_directory=True, file_content=TENTACLES_PYTHON_INIT_CONTENT):
        if not os.path.exists(path):
            if is_directory:
                if not os.path.isdir(path):
                    os.makedirs(path)
            else:
                if not os.path.isfile(path):
                    # should be used for python init.py files only
                    with open(path, "w+") as file:
                        file.write(file_content)

    @staticmethod
    def _get_tentacles_arch():
        tentacles_content_folder = {
                    TENTACLES_EVALUATOR_PATH: [
                        TENTACLES_EVALUATOR_REALTIME_PATH,
                        TENTACLES_EVALUATOR_SOCIAL_PATH,
                        TENTACLES_EVALUATOR_TA_PATH,
                        TENTACLES_EVALUATOR_STRATEGIES_PATH,
                        TENTACLES_EVALUATOR_UTIL_PATH
                    ],
                    TENTACLES_TRADING_PATH: [
                        TENTACLES_TRADING_MODE_PATH
                    ]
                }
        tentacle_architecture = {
            TENTACLES_PATH: [tentacles_content_folder, {TENTACLES_TEST_PATH: tentacles_content_folder}]
        }
        tentacle_extremity_architecture = copy.deepcopy(TENTACLES_INSTALL_FOLDERS)
        return tentacle_architecture, tentacle_extremity_architecture

    @staticmethod
    def _check_format(component):
        purified_name = component.rstrip(",+.; ")
        purified_name = purified_name.strip(",+.; ")
        return purified_name

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

    @staticmethod
    def _has_required_package(package, component_name, component_version=None):
        if component_name in package:
            component = package[component_name]
            if component_version:
                return component[TENTACLE_MODULE_VERSION] == component_version
            else:
                return True
        return False

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
    def _create_localization_from_type(localization, module_type, module_subtype, file, tests=False):
        # create path from types
        test_folder_if_required = ""
        if tests:
            test_folder_if_required = "/{0}".format(TENTACLES_TEST_PATH)
        if module_subtype:
            return "{0}{1}/{2}/{3}/{4}".format(localization,
                                               test_folder_if_required,
                                               module_type,
                                               module_subtype,
                                               file)
        else:
            return "{0}{1}/{2}/{3}".format(localization,
                                           test_folder_if_required,
                                           module_type,
                                           file)

    @staticmethod
    def _create_path_from_type(module_type, module_subtype, target_folder, tests=False):
        # create path from types
        test_folder_if_required = ""
        if tests:
            test_folder_if_required = "/{0}".format(TENTACLES_TEST_PATH)
        if module_subtype:
            return "{0}{1}/{2}/{3}/{4}".format(TENTACLES_PATH,
                                               test_folder_if_required,
                                               TENTACLE_TYPES[module_type],
                                               TENTACLE_TYPES[module_subtype],
                                               target_folder)
        else:
            return "{0}{1}/{2}/{4}".format(TENTACLES_PATH,
                                           test_folder_if_required,
                                           TENTACLE_TYPES[module_type],
                                           target_folder)

    @staticmethod
    def _parse_module(package):
        return {
            TENTACLE_MODULE_NAME: package[TENTACLE_MODULE_NAME],
            TENTACLE_MODULE_TYPE: package[TENTACLE_MODULE_TYPE],
            TENTACLE_MODULE_SUBTYPE: package[TENTACLE_MODULE_SUBTYPE]
            if TENTACLE_MODULE_SUBTYPE in package else None,
            TENTACLE_MODULE_VERSION: package[TENTACLE_MODULE_VERSION],
            TENTACLE_MODULE_REQUIREMENTS: TentacleManager._extract_tentacle_requirements(package),
            TENTACLE_MODULE_TESTS: TentacleManager._extract_tentacle_tests(package),
            TENTACLE_MODULE_CONFIG_FILES: package[TENTACLE_MODULE_CONFIG_FILES]
            if TENTACLE_MODULE_CONFIG_FILES in package else None
        }

    @staticmethod
    def _get_full_module_identifier(module_name, module_version):
        return "{0}{1}{2}".format(module_name, TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR, module_version)

    @staticmethod
    def _parse_version(version):
        return [int(value) for value in version.split(".") if value]

    @staticmethod
    def _is_first_version_superior(first_version, second_version):
        first_version_data = TentacleManager._parse_version(first_version)
        second_version_data = TentacleManager._parse_version(second_version)

        if len(second_version_data) > len(first_version_data):
            return False
        else:
            for index, value in enumerate(first_version_data):
                if len(second_version_data) > index and second_version_data[index] > value:
                    return False
        return first_version_data != second_version_data

    @staticmethod
    def _extract_tentacle_tests(module):
        if TENTACLE_MODULE_TESTS in module:
            tests = []
            for component in module[TENTACLE_MODULE_TESTS]:
                tests = tests + component.split(TENTACLE_MODULE_LIST_SEPARATOR)
            return [test.strip() for test in tests]
        return None

    @staticmethod
    def _extract_tentacle_requirements(module):
        if TENTACLE_MODULE_REQUIREMENTS in module:
            requirements = []
            for component in module[TENTACLE_MODULE_REQUIREMENTS]:
                requirements = requirements + component.split(TENTACLE_MODULE_LIST_SEPARATOR)
            return [TentacleManager._parse_requirements(req.strip()) for req in requirements]
        return None

    @staticmethod
    def _parse_requirements(requirement):
        requirement_info = requirement.split(TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR)
        return {TENTACLE_MODULE_NAME: requirement_info[0],
                TENTACLE_MODULE_VERSION: requirement_info[1] if len(requirement_info) > 1 else None,
                TENTACLE_MODULE_REQUIREMENT_WITH_VERSION: requirement}

    @staticmethod
    def _is_module_in_list(module_name, module_version, module_list):
        if not module_version:
            for module in module_list:
                if module.split(TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR)[0] == module_name:
                    return True
            return False
        else:
            return TentacleManager._get_full_module_identifier(module_name, module_version) \
                   in module_list

    @staticmethod
    def _parse_module_file(package_content, description_list):
        min_description_length = 10
        description_pos = package_content.find(TENTACLE_MODULE_DESCRIPTION)
        if description_pos > -1:
            description_begin_pos = package_content.find("{")
            description_end_pos = package_content.find("}") + 1
            if description_end_pos - description_begin_pos > min_description_length:
                description_raw = package_content[description_begin_pos:description_end_pos]
                description = json.loads(description_raw)
                module_description = TentacleManager._parse_module(description)
                description_list[module_description[TENTACLE_MODULE_NAME]] = module_description

    @staticmethod
    def _check_path(path):
        last_path_folder = path.split("/")[-1]
        return last_path_folder in TENTACLES_INSTALL_FOLDERS

    @staticmethod
    def _read_tentacles(path, description_list):
        for file_name in os.listdir(path):
            if TentacleManager._check_path(path) and file_name.endswith(".py") \
                    and file_name != PYTHON_INIT_FILE:
                with open("{0}/{1}".format(path, file_name), "r") as module:
                    TentacleManager._parse_module_file(module.read(), description_list)
            else:
                file_name = "{0}/{1}".format(path, file_name)
                if os.path.isdir(file_name) and not path.startswith('.'):
                    TentacleManager._read_tentacles(file_name, description_list)

    @staticmethod
    def _update_init_file(action, init_file, line_in_init):
        init_content = ""
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

    @staticmethod
    def _add_evaluator_to_evaluator_config_content(evaluator_type, evaluator_config_content,
                                                   evaluator_list, activated=False):
        from evaluator.Util.advanced_manager import AdvancedManager
        changed_something = False
        current_evaluator_list = AdvancedManager.create_default_evaluator_types_list(evaluator_type)
        for eval_class in current_evaluator_list:
            if not eval_class.get_name() in evaluator_config_content:
                evaluator_config_content[eval_class.get_name()] = activated
                changed_something = True
        evaluator_list += current_evaluator_list
        return changed_something

    @staticmethod
    def _update_evaluator_config_file(evaluator_config_file=CONFIG_EVALUATOR_FILE_PATH):

        logger = logging.getLogger(TentacleManager.__name__)
        try:
            from evaluator.RealTime import RealTimeEvaluator
            from evaluator.Social import SocialEvaluator
            from evaluator.Strategies import StrategiesEvaluator
            from evaluator.TA import TAEvaluator

            logger.info("Updating {} using new data...".format(evaluator_config_file))
            config_content = {}
            changed_something = False
            if os.path.isfile(evaluator_config_file):
                with open(evaluator_config_file, "r") as evaluator_config_file_r:
                    default_config_file_content = evaluator_config_file_r.read()
                    try:
                        config_content = json.loads(default_config_file_content)
                    except Exception:
                        pass
            if os.path.isfile(CONFIG_DEFAULT_EVALUATOR_FILE):
                with open(CONFIG_DEFAULT_EVALUATOR_FILE, "r") as default_evaluator_config_file_r:
                    default_config_file_content = default_evaluator_config_file_r.read()
                    default_config_content = json.loads(default_config_file_content)
                    for key, val in default_config_content.items():
                        if key not in config_content:
                            config_content[key] = val
                            changed_something = True

            evaluator_list = []
            evaluators_in_config = [TAEvaluator, SocialEvaluator, RealTimeEvaluator, StrategiesEvaluator]
            for evaluator_in_config in evaluators_in_config:
                changed_something = TentacleManager._add_evaluator_to_evaluator_config_content(
                    evaluator_in_config, config_content, evaluator_list) or changed_something

            to_remove = []
            str_evaluator_list = [e.get_name() for e in evaluator_list]
            for key in config_content.keys():
                if key not in str_evaluator_list:
                    to_remove.append(key)

            for key_to_remove in to_remove:
                config_content.pop(key_to_remove)
                changed_something = True

            if changed_something:
                with open(evaluator_config_file, "w+") as evaluator_config_file_w:
                    evaluator_config_file_w.write(json.dumps(config_content, indent=4, sort_keys=True))
                    logger.info("{} has been updated".format(evaluator_config_file))
            else:
                logger.info("Nothing to update in {}".format(evaluator_config_file))
        except Exception as e:
            logger.exception(e)
            logger.error("Something went wrong: {}.\nIf Octobot is now working after this, you should re-install your "
                         "tentacles (start.py -p install all).\nIf this problem keeps appearing, try to reset all the "
                         "tentacles (start.py -p reset_tentacles).".format(e))


class TentacleManagerActions(Enum):
    INSTALL = 1
    UNINSTALL = 2
    UPDATE = 3
