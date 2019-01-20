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
import os

import tools.tentacle_manager.tentacle_package_util as TentaclePackageUtil
import tools.tentacle_manager.tentacle_util as TentacleUtil

from config import TENTACLE_PACKAGE_DESCRIPTION, EVALUATOR_DEFAULT_FOLDER, \
    TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION, \
    TENTACLE_DESCRIPTION_IS_URL, TENTACLE_TYPES, EVALUATOR_CONFIG_FOLDER, TENTACLE_MODULE_NAME, TENTACLE_MODULE_TYPE, \
    TENTACLE_MODULE_SUBTYPE, TENTACLE_MODULE_VERSION, TENTACLE_MODULE_CONFIG_FILES, TENTACLE_MODULE_REQUIREMENTS, \
    TENTACLE_MODULE_REQUIREMENT_WITH_VERSION, TENTACLES_PATH, PYTHON_INIT_FILE, TENTACLE_MODULE_TESTS, \
    TentacleManagerActions, CONFIG_DEFAULT_EVALUATOR_FILE, CONFIG_EVALUATOR_FILE_PATH, TENTACLE_MODULE_DEV, \
    TENTACLE_PACKAGE_NAME, TENTACLE_MODULE_RESOURCE_FILES, EVALUATOR_RESOURCE_FOLDER, CONFIG_TRADING_FILE_PATH, \
    CONFIG_DEFAULT_TRADING_FILE


class TentaclePackageManager:
    def __init__(self, config, tentacle_manager):
        self.config = config
        self.tentacle_manager = tentacle_manager
        self.logger = get_logger(self.__class__.__name__)
        self.just_processed_modules = []
        self.installed_modules = {}
        self.max_steps = None
        self.current_step = 1

    def _process_action_on_module(self, action, module_type, module_subtype,
                                  module_version, module_file_content, module_test_files, target_folder, module_name):

        if module_subtype in TENTACLE_TYPES and (module_subtype or module_subtype in TENTACLE_TYPES):

            did_something = False

            # Update module file
            module_file_dir = TentacleUtil.create_path_from_type(module_type, module_subtype, target_folder)

            module_file_path = "{0}/{1}.py".format(module_file_dir, module_name)

            # Write the new file in locations
            if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                # Install package in evaluator
                with open(module_file_path, "w") as module_file:
                    module_file.write(module_file_content)
                    did_something = True

            # Remove package line from init file
            elif action == TentacleManagerActions.UNINSTALL:
                try:
                    if os.path.exists(module_file_path):
                        os.remove(module_file_path)
                        did_something = True
                except OSError:
                    did_something = False

            # Update local __init__
            line_in_init = "from .{0} import *\n".format(module_name)
            init_file = "{0}/{1}/{2}/{3}/{4}".format(TENTACLES_PATH,
                                                     TENTACLE_TYPES[module_type],
                                                     TENTACLE_TYPES[module_subtype],
                                                     target_folder,
                                                     PYTHON_INIT_FILE)

            self.update_init_file(action, init_file, line_in_init)

            # Update module test files
            test_file_dir = TentacleUtil.create_path_from_type(module_type, module_subtype, target_folder, True)
            for test_file, test_file_content in module_test_files.items():
                module_test_file_path = "{0}/{1}.py".format(test_file_dir, test_file)

                # Write the new file in locations
                if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                    # Install package in evaluator
                    with open(module_test_file_path, "w") as installed_module_test_file:
                        installed_module_test_file.write(test_file_content)

                # Remove package line from init file
                elif action == TentacleManagerActions.UNINSTALL:
                    try:
                        os.remove(module_test_file_path)
                    except OSError:
                        pass

            if action == TentacleManagerActions.INSTALL:
                self.logger.info("{0}{1} {2} successfully installed in: {3}"
                                 .format(self._format_current_step(), module_name, module_version, module_file_dir))
            elif action == TentacleManagerActions.UNINSTALL:
                if did_something:
                    self.logger.info("{0}{1} {2} successfully uninstalled (file: {3})"
                                     .format(self._format_current_step(), module_name, module_version, module_file_dir))
            elif action == TentacleManagerActions.UPDATE:
                self.logger.info("{0}{1} successfully updated to version {2} in: {3}"
                                 .format(self._format_current_step(), module_name, module_version, module_file_dir))
            self.just_processed_modules.append(TentacleUtil.get_full_module_identifier(module_name, module_version))
            return did_something

        else:
            raise Exception("Tentacle type not found")

    def process_module(self, action, package, module_name, package_localisation, is_url, target_folder, package_name):
        parsed_module = TentacleUtil.parse_module_header(package[module_name])
        module_type = parsed_module[TENTACLE_MODULE_TYPE]
        module_subtype = parsed_module[TENTACLE_MODULE_SUBTYPE]
        module_tests = parsed_module[TENTACLE_MODULE_TESTS]
        module_file_content = ""
        module_dev = parsed_module[TENTACLE_MODULE_DEV]
        module_test_files = {test: "" for test in module_tests} if module_tests else {}

        if TentacleUtil.install_on_development(self.config, module_dev):
            if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                module_loc = "{0}.py".format(TentacleUtil.create_localization_from_type(package_localisation,
                                                                                        module_type,
                                                                                        module_subtype,
                                                                                        module_name))

                if is_url:
                    module_file_content = TentaclePackageUtil.get_package_file_content_from_url(module_loc)
                else:
                    with open(module_loc, "r") as module_file:
                        module_file_content = module_file.read()

                module_file_content = TentaclePackageUtil.add_package_name(module_file_content, package_name)

                if module_test_files:
                    for test in module_tests:
                        test_loc = "{0}.py".format(TentacleUtil.create_localization_from_type(package_localisation,
                                                                                              module_type,
                                                                                              module_subtype,
                                                                                              test,
                                                                                              True))

                        if is_url:
                            module_test_files[test] = TentaclePackageUtil.get_package_file_content_from_url(test_loc)
                        else:
                            with open(test_loc, "r") as module_file:
                                module_test_files[test] = module_file.read()

            if self._process_action_on_module(action, module_type, module_subtype,
                                              parsed_module[TENTACLE_MODULE_VERSION],
                                              module_file_content, module_test_files, target_folder, module_name):
                # manage module config
                self._try_action_on_config_or_resources(action, package, module_name, is_url, package_localisation)

            if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
                self._try_action_on_requirements(action, package, module_name, package_name)
        else:
            self.logger.warning("{0} is currently on development, "
                                "it will not be installed (to install it anyway, "
                                "add \"DEV-MODE\": true in your config.json)".format(module_name))

    def _should_do_something(self, action, module_name, module_version, need_this_exact_version=False, requiring=None):
        if action == TentacleManagerActions.UPDATE:
            if TentacleUtil.is_module_in_list(module_name, None, self.installed_modules):
                installed_version = self.installed_modules[module_name][TENTACLE_MODULE_VERSION]
                if not need_this_exact_version:
                    new_version_available = TentacleUtil.is_first_version_superior(module_version, installed_version)
                    if not new_version_available:
                        self.logger.info("{0}{1} version {2} is already up to date"
                                         .format(self._format_current_step(), module_name, installed_version))
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
                    self.logger.error("can't find tentacle: {0} required for {1} in installed tentacles. "
                                      "Try to install the required tentacle".format(module_name, requiring))
                else:
                    self.logger.info("new tentacle found in tentacles packages: {0}. "
                                     "You can install it using the command: {1}"
                                     .format(module_name, "start.py -p install {0}".format(module_name)))

            return False
        else:
            return True

    def try_action_on_tentacles_package(self, action, package, target_folder):
        package_description = package[TENTACLE_PACKAGE_DESCRIPTION]
        package_localisation = package_description[TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION]
        is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
        package_name = package_description[TENTACLE_PACKAGE_NAME]
        for tentacle_module in package:
            try:
                if tentacle_module != TENTACLE_PACKAGE_DESCRIPTION and \
                        not self._has_just_processed_module(tentacle_module,
                                                            package[tentacle_module][TENTACLE_MODULE_VERSION]) and \
                        self._should_do_something(action, tentacle_module,
                                                  package[tentacle_module][TENTACLE_MODULE_VERSION]):
                    self.process_module(action, package, tentacle_module, package_localisation, is_url, target_folder,
                                        package_name)
            except Exception as e:
                error = "failed for tentacle module '{0}' ({1})".format(tentacle_module, e)
                if action == TentacleManagerActions.INSTALL:
                    self.logger.error("Installation {0}".format(error))
                elif action == TentacleManagerActions.UNINSTALL:
                    self.logger.error("Uninstalling {0}".format(error))
                elif action == TentacleManagerActions.UPDATE:
                    self.logger.error("Updating {0}".format(error))
            self.inc_current_step()

    def _try_action_on_requirements(self, action, package, module_name, package_name):
        parsed_module = TentacleUtil.parse_module_header(package[module_name])
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
                            req_package, _, localisation, is_url, destination, _ = self.tentacle_manager. \
                                get_package_in_lists(requirement_module_name, requirement_module_version)

                            if req_package:
                                self.process_module(action, req_package, requirement_module_name,
                                                    localisation, is_url, destination, package_name)
                                applied_modules.append(requirement_module_name)
                            else:
                                raise Exception("module requirement '{0}' not found in package lists"
                                                .format(requirement_data[TENTACLE_MODULE_REQUIREMENT_WITH_VERSION]))

                        except Exception as e:
                            error = "failed for tentacle module requirement '{0}' of module {1} ({2})" \
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
                    req_package, _, localisation, is_url, destination, _ = self.tentacle_manager. \
                        get_package_in_lists(module_name)
                    if req_package:
                        self.process_module(TentacleManagerActions.UNINSTALL, req_package, module_name,
                                            localisation, is_url, destination, package_name)

                elif action == TentacleManagerActions.INSTALL:
                    # uninstall module and requirements
                    for module_to_remove in applied_modules:
                        req_package, _, localisation, is_url, destination, _ = self.tentacle_manager. \
                            get_package_in_lists(module_to_remove)
                        if req_package:
                            self.process_module(TentacleManagerActions.UNINSTALL, req_package, module_to_remove,
                                                localisation, is_url, destination, package_name)

    def _try_action_on_config_or_resources(self, action, package, module_name, is_url, package_localisation):
        parsed_module = TentacleUtil.parse_module_header(package[module_name])

        file_dir = TentacleUtil.create_path_from_type(parsed_module[TENTACLE_MODULE_TYPE],
                                                      parsed_module[TENTACLE_MODULE_SUBTYPE], "")

        if parsed_module[TENTACLE_MODULE_CONFIG_FILES]:
            for config_file in parsed_module[TENTACLE_MODULE_CONFIG_FILES]:
                config_file_path = "{0}{1}/{2}".format(file_dir, EVALUATOR_CONFIG_FOLDER, config_file)
                default_config_file_path = "{0}{1}/{2}/{3}".format(file_dir, EVALUATOR_CONFIG_FOLDER,
                                                                   EVALUATOR_DEFAULT_FOLDER, config_file)

                self._try_action_on_config_or_resource_file(action,
                                                            module_name,
                                                            package_localisation,
                                                            is_url,
                                                            parsed_module,
                                                            config_file,
                                                            config_file_path,
                                                            default_file_path=default_config_file_path)

        if parsed_module[TENTACLE_MODULE_RESOURCE_FILES]:
            for res_file in parsed_module[TENTACLE_MODULE_RESOURCE_FILES]:
                res_file_path = "{0}{1}/{2}".format(file_dir, EVALUATOR_RESOURCE_FOLDER, res_file)

                self._try_action_on_config_or_resource_file(action,
                                                            module_name,
                                                            package_localisation,
                                                            is_url,
                                                            parsed_module,
                                                            res_file,
                                                            res_file_path,
                                                            read_as_bytes=True)

    def _try_action_on_config_or_resource_file(self, action,
                                               module_name,
                                               package_localisation,
                                               is_url,
                                               parsed_module,
                                               file,
                                               file_path,
                                               default_file_path=None,
                                               read_as_bytes=False):

        if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:

            try:
                # get config file content from localization
                module_loc = TentacleUtil.create_localization_from_type(package_localisation,
                                                                        parsed_module[TENTACLE_MODULE_TYPE],
                                                                        parsed_module[TENTACLE_MODULE_SUBTYPE],
                                                                        file)

                if is_url:
                    config_file_content = TentaclePackageUtil.get_package_file_content_from_url(module_loc,
                                                                                                as_bytes=read_as_bytes)
                else:
                    with open(module_loc, "rb" if read_as_bytes else "r") as module_file:
                        config_file_content = module_file.read()

                # install local file content
                if action == TentacleManagerActions.INSTALL:
                    with open(file_path, "wb" if read_as_bytes else "w") as new_file:
                        new_file.write(config_file_content)

                # copy into default
                if default_file_path:
                    with open(default_file_path, "wb" if read_as_bytes else "w") as new_default_file:
                        new_default_file.write(config_file_content)

                    if action == TentacleManagerActions.UPDATE:
                        self.logger.info("{0} configuration / resource file for {1} module ignored to save the current "
                                         "configuration. The default configuration file has been updated in: {2}."
                                         .format(file, module_name, default_file_path))

            except Exception as e:
                raise Exception("Fail to install configuration / resource : {}".format(e))

        elif action == TentacleManagerActions.UNINSTALL:
            try:
                os.remove(file_path)

                if default_file_path:
                    os.remove(default_file_path)
            except OSError:
                pass

    def _has_just_processed_module(self, module_name, module_version):
        return TentacleUtil.is_module_in_list(module_name, module_version, self.just_processed_modules)

    @staticmethod
    def get_installed_modules():
        modules = {}
        # Foreach folder (not hidden)
        for root_dir in os.listdir(os.getcwd()):
            if os.path.isdir(root_dir) and not root_dir.startswith('.'):
                TentaclePackageUtil.read_tentacles(root_dir, modules)
        return modules

    def _format_current_step(self):
        return "{0}/{1}: ".format(self.current_step, self.max_steps) if self.max_steps is not None else ""

    def set_max_steps(self, max_steps):
        self.max_steps = max_steps

    def set_installed_modules(self, installed_modules):
        self.installed_modules = installed_modules

    def inc_current_step(self):
        self.current_step += 1

    @staticmethod
    def update_init_file(action, init_file, line_in_init):
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
    def _log_config_file_update_exception(logger, exception):
        logger.exception(exception)
        logger.error(f"Something went wrong when checking installed tentacles: {exception}.\nIf Octobot is now "
                     "working after this, you should re-install your tentacles (start.py -p install all).\nIf this "
                     "problem keeps appearing, try to reset all tentacles (start.py -p reset_tentacles).")

    @staticmethod
    def update_evaluator_config_file(evaluator_config_file=CONFIG_EVALUATOR_FILE_PATH):

        logger = get_logger(TentaclePackageManager.__name__)
        try:
            logger.info(f"Updating {evaluator_config_file} using new data...")

            from evaluator.RealTime import RealTimeEvaluator
            from evaluator.Social import SocialEvaluator
            from evaluator.Strategies import StrategiesEvaluator
            from evaluator.TA import TAEvaluator

            evaluators_in_config = [TAEvaluator, SocialEvaluator, RealTimeEvaluator, StrategiesEvaluator]

            TentaclePackageUtil.update_config_file(evaluator_config_file, CONFIG_DEFAULT_EVALUATOR_FILE,
                                                   evaluators_in_config)
        except Exception as e:
            TentaclePackageManager._log_config_file_update_exception(logger, e)

    @staticmethod
    def update_trading_config_file(trading_config_file=CONFIG_TRADING_FILE_PATH):

        logger = get_logger(TentaclePackageManager.__name__)
        try:
            logger.info(f"Updating {trading_config_file} using new data...")

            from trading.trader.modes import AbstractTradingMode

            trading_modes_in_config = [AbstractTradingMode]

            TentaclePackageUtil.update_config_file(trading_config_file, CONFIG_DEFAULT_TRADING_FILE,
                                                   trading_modes_in_config)
        except Exception as e:
            TentaclePackageManager._log_config_file_update_exception(logger, e)
