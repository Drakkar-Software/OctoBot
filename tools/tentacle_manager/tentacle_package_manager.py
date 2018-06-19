import logging
import os
import json

import tools.tentacle_manager.tentacle_package_util as TentaclePackageUtil
import tools.tentacle_manager.tentacle_util as TentacleUtil

from config.cst import TENTACLE_DESCRIPTION, EVALUATOR_DEFAULT_FOLDER, TENTACLE_DESCRIPTION_LOCALISATION, \
    TENTACLE_DESCRIPTION_IS_URL, TENTACLE_TYPES, EVALUATOR_CONFIG_FOLDER, TENTACLE_MODULE_NAME, TENTACLE_MODULE_TYPE, \
    TENTACLE_MODULE_SUBTYPE, TENTACLE_MODULE_VERSION, TENTACLE_MODULE_CONFIG_FILES, TENTACLE_MODULE_REQUIREMENTS, \
    TENTACLE_MODULE_REQUIREMENT_WITH_VERSION, TENTACLES_PATH, PYTHON_INIT_FILE, TENTACLE_MODULE_TESTS, \
    TentacleManagerActions, CONFIG_DEFAULT_EVALUATOR_FILE, CONFIG_EVALUATOR_FILE_PATH


class TentaclePackageManager:
    def __init__(self, config, tentacle_manager):
        self.config = config
        self.tentacle_manager = tentacle_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.just_processed_modules = []
        self.installed_modules = {}

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
                self.logger.info("{0} {1} successfully installed in: {2}"
                                 .format(module_name, module_version, module_file_dir))
            elif action == TentacleManagerActions.UNINSTALL:
                if did_something:
                    self.logger.info("{0} {1} successfully uninstalled (file: {2})"
                                     .format(module_name, module_version, module_file_dir))
            elif action == TentacleManagerActions.UPDATE:
                self.logger.info("{0} successfully updated to version {1} in: {2}"
                                 .format(module_name, module_version, module_file_dir))
            self.just_processed_modules.append(TentacleUtil.get_full_module_identifier(module_name, module_version))
            return did_something

        else:
            raise Exception("Tentacle type not found")

    def process_module(self, action, package, module_name, package_localisation, is_url, target_folder):
        parsed_module = TentacleUtil.parse_module_header(package[module_name])
        module_type = parsed_module[TENTACLE_MODULE_TYPE]
        module_subtype = parsed_module[TENTACLE_MODULE_SUBTYPE]
        module_tests = parsed_module[TENTACLE_MODULE_TESTS]
        module_file_content = ""
        module_test_files = {test: "" for test in module_tests} if module_tests else {}

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

        if self._process_action_on_module(action, module_type, module_subtype, parsed_module[TENTACLE_MODULE_VERSION],
                                          module_file_content, module_test_files, target_folder, module_name):
            # manage module config
            self._try_action_on_config(action, package, module_name, is_url, package_localisation)

        if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:
            self._try_action_on_requirements(action, package, module_name)

    def _should_do_something(self, action, module_name, module_version, need_this_exact_version=False, requiring=None):
        if action == TentacleManagerActions.UPDATE:
            if TentacleUtil.is_module_in_list(module_name, None, self.installed_modules):
                installed_version = self.installed_modules[module_name][TENTACLE_MODULE_VERSION]
                if not need_this_exact_version:
                    new_version_available = TentacleUtil.is_first_version_superior(module_version, installed_version)
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
        package_description = package[TENTACLE_DESCRIPTION]
        package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
        is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
        for tentacle_module in package:
            try:
                if tentacle_module != TENTACLE_DESCRIPTION and \
                        not self._has_just_processed_module(tentacle_module,
                                                            package[tentacle_module][TENTACLE_MODULE_VERSION]) and \
                        self._should_do_something(action, tentacle_module,
                                                  package[tentacle_module][TENTACLE_MODULE_VERSION]):
                    self.process_module(action, package, tentacle_module, package_localisation, is_url, target_folder)
            except Exception as e:
                error = "failed for tentacle module '{0}' ({1})".format(tentacle_module, e)
                if action == TentacleManagerActions.INSTALL:
                    self.logger.error("Installation {0}".format(error))
                elif action == TentacleManagerActions.UNINSTALL:
                    self.logger.error("Uninstalling {0}".format(error))
                elif action == TentacleManagerActions.UPDATE:
                    self.logger.error("Updating {0}".format(error))

    def _try_action_on_requirements(self, action, package, module_name):
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
                            req_package, _, localisation, is_url, destination = self.tentacle_manager.\
                                get_package_in_lists(requirement_module_name, requirement_module_version)

                            if req_package:
                                self.process_module(action, req_package, requirement_module_name,
                                                    localisation, is_url, destination)
                                applied_modules.append(requirement_module_name)
                            else:
                                raise Exception("module requirement '{0}' not found in package lists"
                                                .format(requirement_data[TENTACLE_MODULE_REQUIREMENT_WITH_VERSION]))

                        except Exception as e:
                            error = "failed for tentacle module requirement '{0}' of module {1} ({2})"\
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
                    req_package, _, localisation, is_url, destination = self.tentacle_manager.\
                        get_package_in_lists(module_name)
                    if req_package:
                        self.process_module(TentacleManagerActions.UNINSTALL, req_package, module_name,
                                            localisation, is_url, destination)

                elif action == TentacleManagerActions.INSTALL:
                    # uninstall module and requirements
                    for module_to_remove in applied_modules:
                        req_package, _, localisation, is_url, destination = self.tentacle_manager.\
                            get_package_in_lists(module_to_remove)
                        if req_package:
                            self.process_module(TentacleManagerActions.UNINSTALL, req_package, module_to_remove,
                                                localisation, is_url, destination)

    def _try_action_on_config(self, action, package, module_name, is_url, package_localisation):
        parsed_module = TentacleUtil.parse_module_header(package[module_name])

        if parsed_module[TENTACLE_MODULE_CONFIG_FILES]:
            for config_file in parsed_module[TENTACLE_MODULE_CONFIG_FILES]:

                file_dir = TentacleUtil.create_path_from_type(parsed_module[TENTACLE_MODULE_TYPE],
                                                              parsed_module[TENTACLE_MODULE_SUBTYPE], "")

                config_file_path = "{0}{1}/{2}".format(file_dir, EVALUATOR_CONFIG_FOLDER, config_file)
                default_config_file_path = "{0}{1}/{2}/{3}".format(file_dir, EVALUATOR_CONFIG_FOLDER,
                                                                   EVALUATOR_DEFAULT_FOLDER, config_file)
                if action == TentacleManagerActions.INSTALL or action == TentacleManagerActions.UPDATE:

                    try:
                        # get config file content from localization
                        module_loc = TentacleUtil.create_localization_from_type(package_localisation,
                                                                                parsed_module[TENTACLE_MODULE_TYPE],
                                                                                parsed_module[TENTACLE_MODULE_SUBTYPE],
                                                                                config_file)

                        if is_url:
                            config_file_content = TentaclePackageUtil.get_package_file_content_from_url(module_loc)
                        else:
                            with open(module_loc, "r") as module_file:
                                config_file_content = module_file.read()

                        # install local config file content
                        if action == TentacleManagerActions.INSTALL:
                            with open(config_file_path, "w") as new_config_file:
                                new_config_file.write(config_file_content)
                        with open(default_config_file_path, "w") as new_default_config_file:
                            new_default_config_file.write(config_file_content)

                        if action == TentacleManagerActions.UPDATE:
                            self.logger.info("{0} configuration file for {1} module ignored to save the current "
                                             "configuration. The default configuration file has been updated in: {2}."
                                             .format(config_file, module_name, default_config_file_path))

                    except Exception as e:
                        raise Exception("Fail to install configuration : {}".format(e))

                elif action == TentacleManagerActions.UNINSTALL:
                    try:
                        os.remove(config_file_path)
                        os.remove(default_config_file_path)
                    except OSError:
                        pass

    def _has_just_processed_module(self, module_name, module_version):
        return TentacleUtil.is_module_in_list(module_name, module_version, self.just_processed_modules)

    def _init_installed_modules(self):
        # Foreach folder (not hidden)
        for root_dir in os.listdir(os.getcwd()):
            if os.path.isdir(root_dir) and not root_dir.startswith('.'):
                TentaclePackageUtil.read_tentacles(root_dir, self.installed_modules)

    def init_installed_modules(self):
        # Foreach folder (not hidden)
        for root_dir in os.listdir(os.getcwd()):
            if os.path.isdir(root_dir) and not root_dir.startswith('.'):
                TentaclePackageUtil.read_tentacles(root_dir, self.installed_modules)

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
    def update_evaluator_config_file(evaluator_config_file=CONFIG_EVALUATOR_FILE_PATH):

        logger = logging.getLogger(TentaclePackageManager.__name__)
        try:
            logger.info("Updating {} using new data...".format(evaluator_config_file))

            from evaluator.RealTime import RealTimeEvaluator
            from evaluator.Social import SocialEvaluator
            from evaluator.Strategies import StrategiesEvaluator
            from evaluator.TA import TAEvaluator

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
                changed_something = TentaclePackageUtil.add_evaluator_to_evaluator_config_content(
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
            logger.error("Something went wrong when checking installed tentacles: {}.\nIf Octobot is now working after "
                         "this, you should re-install your tentacles (start.py -p install all).\nIf this problem keeps "
                         "appearing, try to reset all tentacles (start.py -p reset_tentacles).".format(e))
