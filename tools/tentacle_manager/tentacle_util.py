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

import os
import shutil
import copy
import json

from config import EVALUATOR_DEFAULT_FOLDER, TENTACLE_TYPES, EVALUATOR_CONFIG_FOLDER, \
    TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR, TENTACLE_MODULE_NAME, TENTACLE_MODULE_TYPE, \
    TENTACLE_MODULE_SUBTYPE, TENTACLE_MODULE_VERSION, TENTACLE_MODULE_CONFIG_FILES, TENTACLE_MODULE_REQUIREMENTS, \
    TENTACLE_MODULE_LIST_SEPARATOR, TENTACLE_MODULE_REQUIREMENT_WITH_VERSION, TENTACLE_MODULE_DESCRIPTION, \
    TENTACLES_INSTALL_FOLDERS, TENTACLES_PATH, TENTACLES_EVALUATOR_PATH, TENTACLES_TRADING_PATH, \
    TENTACLES_EVALUATOR_REALTIME_PATH, TENTACLES_EVALUATOR_TA_PATH, TENTACLES_EVALUATOR_SOCIAL_PATH, \
    TENTACLES_EVALUATOR_STRATEGIES_PATH, TENTACLES_EVALUATOR_UTIL_PATH, TENTACLES_TRADING_MODE_PATH, \
    TENTACLES_PYTHON_INIT_CONTENT, PYTHON_INIT_FILE, TENTACLE_MODULE_TESTS, TENTACLES_TEST_PATH, TENTACLE_MODULE_DEV, \
    TENTACLE_PACKAGE, TENTACLE_MODULE_RESOURCE_FILES, EVALUATOR_RESOURCE_FOLDER, \
    TENTACLE_CURRENT_MINIMUM_DEFAULT_TENTACLES_VERSION
from tools.config_manager import ConfigManager
from tools.logging.logging_util import get_logger


def tentacles_arch_exists() -> bool:
    try:
        import tentacles
        return os.path.exists(TENTACLES_PATH) and os.path.exists(f"{TENTACLES_PATH}/{TENTACLES_TEST_PATH}")
    except ImportError:
        return False


def delete_tentacles_arch():
    if tentacles_arch_exists():
        shutil.rmtree(TENTACLES_PATH)


def check_format(component):
    purified_name = component.rstrip(",+.; ")
    purified_name = purified_name.strip(",+.; ")
    return purified_name


def has_required_package(package, component_name, component_version=None):
    if component_name in package:
        component = package[component_name]
        if component_version:
            return component[TENTACLE_MODULE_VERSION] == component_version
        else:
            return True
    return False


def create_missing_tentacles_arch():
    found_existing_installation = False
    tentacle_architecture, tentacle_extremity_architecture = get_tentacles_arch()
    for tentacle_root, subdir in tentacle_architecture.items():
        found_existing_installation = not _find_or_create(tentacle_root)
        init_path = os.path.join(tentacle_root, PYTHON_INIT_FILE)
        _find_or_create(init_path, False, "")
        for tentacle_dir in subdir:
            for tentacle_type_dir, types_subdir in tentacle_dir.items():
                type_path = os.path.join(tentacle_root, tentacle_type_dir)
                _find_or_create(type_path)
                init_path = os.path.join(type_path, PYTHON_INIT_FILE)
                _find_or_create(init_path, False, "")
                if isinstance(types_subdir, dict):
                    for tentacle_subtype_dir, types_subsubdir in types_subdir.items():
                        test_type_path = os.path.join(type_path, tentacle_subtype_dir)
                        _find_or_create(test_type_path)
                        init_path = os.path.join(test_type_path, PYTHON_INIT_FILE)
                        _find_or_create(init_path, False, "")
                        _create_arch_module_extremity(tentacle_extremity_architecture,
                                                      types_subsubdir, test_type_path, False, False)
                else:
                    _create_arch_module_extremity(tentacle_extremity_architecture, types_subdir, type_path)
    return found_existing_installation


def _create_arch_module_extremity(architecture, types_subdir, type_path, with_init_config=True, with_init_res=True):
    for module_type in types_subdir:
        path = os.path.join(type_path, module_type)
        _find_or_create(path)
        for extremity_folder in architecture:
            module_content_path = os.path.join(path, extremity_folder)
            # add Advanced etc folders
            _find_or_create(module_content_path)
            init_path = os.path.join(module_content_path, PYTHON_INIT_FILE)
            _find_or_create(init_path, False, "")
        # add init.py file
        init_path = os.path.join(path, PYTHON_INIT_FILE)
        _find_or_create(init_path, False)

        if with_init_config:
            module_config_path = os.path.join(path, EVALUATOR_CONFIG_FOLDER)
            _find_or_create(module_config_path)
            module_default_config_path = os.path.join(module_config_path, EVALUATOR_DEFAULT_FOLDER)
            _find_or_create(module_default_config_path)

        if with_init_res:
            module_res_path = os.path.join(path, EVALUATOR_RESOURCE_FOLDER)
            _find_or_create(module_res_path)


def get_tentacles_arch():
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
        return True
    return False


def parse_module_header(module_header_content):
    return {
        TENTACLE_MODULE_NAME: module_header_content[TENTACLE_MODULE_NAME],
        TENTACLE_MODULE_TYPE: module_header_content[TENTACLE_MODULE_TYPE],
        TENTACLE_MODULE_SUBTYPE: module_header_content[TENTACLE_MODULE_SUBTYPE]
        if TENTACLE_MODULE_SUBTYPE in module_header_content else None,
        TENTACLE_MODULE_VERSION: module_header_content[TENTACLE_MODULE_VERSION],
        TENTACLE_MODULE_REQUIREMENTS: extract_tentacle_requirements(module_header_content),
        TENTACLE_MODULE_TESTS: extract_tentacle_tests(module_header_content),
        TENTACLE_MODULE_CONFIG_FILES: module_header_content[TENTACLE_MODULE_CONFIG_FILES]
        if TENTACLE_MODULE_CONFIG_FILES in module_header_content else None,
        TENTACLE_MODULE_RESOURCE_FILES: module_header_content[TENTACLE_MODULE_RESOURCE_FILES]
        if TENTACLE_MODULE_RESOURCE_FILES in module_header_content else None,
        TENTACLE_MODULE_DEV: module_header_content[TENTACLE_MODULE_DEV]
        if TENTACLE_MODULE_DEV in module_header_content else None,
        TENTACLE_PACKAGE: module_header_content[TENTACLE_PACKAGE]
        if TENTACLE_PACKAGE in module_header_content else "???",
    }


def extract_tentacle_requirements(module):
    if TENTACLE_MODULE_REQUIREMENTS in module:
        requirements = []
        for component in module[TENTACLE_MODULE_REQUIREMENTS]:
            requirements = requirements + component.split(TENTACLE_MODULE_LIST_SEPARATOR)
        return [parse_requirements(req.strip()) for req in requirements]
    return None


def parse_requirements(requirement):
    requirement_info = requirement.split(TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR)
    return {TENTACLE_MODULE_NAME: requirement_info[0],
            TENTACLE_MODULE_VERSION: requirement_info[1] if len(requirement_info) > 1 else None,
            TENTACLE_MODULE_REQUIREMENT_WITH_VERSION: requirement}


def extract_tentacle_tests(module):
    if TENTACLE_MODULE_TESTS in module:
        tests = []
        for component in module[TENTACLE_MODULE_TESTS]:
            tests = tests + component.split(TENTACLE_MODULE_LIST_SEPARATOR)
        return [test.strip() for test in tests]
    return None


def parse_module_file(module_file_content, description_list):
    min_description_length = 10
    description_pos = module_file_content.find(TENTACLE_MODULE_DESCRIPTION)
    if description_pos > -1:
        description_begin_pos = module_file_content.find("{")
        description_end_pos = module_file_content.find("}") + 1
        if description_end_pos - description_begin_pos > min_description_length:
            description_raw = module_file_content[description_begin_pos:description_end_pos]
            description = json.loads(description_raw)
            module_description = parse_module_header(description)
            description_list[module_description[TENTACLE_MODULE_NAME]] = module_description


def create_localization_from_type(localization, module_type, module_subtype, file, tests=False):
    # create path from types
    test_folder_if_required = ""
    if tests:
        test_folder_if_required = f"/{TENTACLES_TEST_PATH}"
    if module_subtype:
        return f"{localization}{test_folder_if_required}/{module_type}/{module_subtype}/{file}"
    else:
        return f"{localization}{test_folder_if_required}/{module_type}/{file}"


def create_path_from_type(module_type, module_subtype, target_folder, tests=False):
    # create path from types
    test_folder_if_required = ""
    if tests:
        test_folder_if_required = f"/{TENTACLES_TEST_PATH}"
    if module_subtype:
        return f"{TENTACLES_PATH}{test_folder_if_required}/{TENTACLE_TYPES[module_type]}/" \
            f"{TENTACLE_TYPES[module_subtype]}/{target_folder}"
    else:
        return f"{TENTACLES_PATH}{test_folder_if_required}/{TENTACLE_TYPES[module_type]}/{target_folder}"


def get_full_module_identifier(module_name, module_version):
    return f"{module_name}{TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR}{module_version}"


def parse_version(version):
    return [int(value) for value in version.split(".") if value]


def is_first_version_superior(first_version, second_version, or_equal=False):
    first_version_data = parse_version(first_version)
    second_version_data = parse_version(second_version)

    if len(second_version_data) > len(first_version_data):
        return False
    else:
        if or_equal and first_version_data == second_version_data:
            return True
        for index, value in enumerate(first_version_data):
            if len(second_version_data) > index and second_version_data[index] > value:
                return False
    return first_version_data != second_version_data


def is_module_in_list(module_name, module_version, module_list):
    if not module_version:
        return any(module.split(TENTACLE_MODULE_REQUIREMENT_VERSION_SEPARATOR)[0] == module_name
                   for module in module_list)
    else:
        return get_full_module_identifier(module_name, module_version) \
               in module_list


def install_on_development(config, module_dev):
    # is not on development
    if module_dev is None or not module_dev:
        return True

    # is on development
    if module_dev and ConfigManager.is_in_dev_mode(config):
        return True

    return False


def _parse_package(tentacle_content):
    description_pos = tentacle_content.find("$tentacle_description")
    if description_pos > -1:
        description_begin_pos = tentacle_content.find("{")
        description_end_pos = tentacle_content.find("}") + 1
        description_raw = tentacle_content[description_begin_pos:description_end_pos]
        return json.loads(description_raw)
    return None


def _read_tentacle(file_name):
    if file_name.endswith(".py"):
        with open(file_name, "r") as tentacle:
            return _parse_package(tentacle.read())


def check_tentacle(path, tentacle, verbose=True):
    logger = get_logger("TentacleChecker")
    try:
        # only check tentacle version for default tentacles
        if path.endswith(EVALUATOR_DEFAULT_FOLDER):
            tentacle_desc = _read_tentacle(os.path.join(path, f"{tentacle}.py"))
            installed_version = tentacle_desc[TENTACLE_MODULE_VERSION]
            if is_first_version_superior(installed_version, TENTACLE_CURRENT_MINIMUM_DEFAULT_TENTACLES_VERSION,
                                         or_equal=True):
                return True
            else:
                if verbose:
                    logger.error(f"Incompatible tentacle {tentacle}: version {installed_version}, "
                                 f"minimum expected: {TENTACLE_CURRENT_MINIMUM_DEFAULT_TENTACLES_VERSION} this tentacle "
                                 f"may not work properly. Please update your tentacles ('start.py -p update {tentacle}' "
                                 f"or 'start.py -p update all')")
                return False
    except Exception as e:
        if verbose:
            logger.error(f"Error when reading tentacle description: {e}")
        return False
