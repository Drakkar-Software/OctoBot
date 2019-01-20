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

import json
import requests
import os

from tools.tentacle_manager import tentacle_util as TentacleUtil
from config import TENTACLES_PUBLIC_LIST, TENTACLES_DEFAULT_BRANCH, TENTACLE_PACKAGE_DESCRIPTION, \
    GITHUB_BASE_URL, GITHUB, TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION, TENTACLE_DESCRIPTION_IS_URL, \
    TENTACLES_INSTALL_FOLDERS, PYTHON_INIT_FILE, TENTACLE_PACKAGE_NAME, TENTACLES_PUBLIC_REPOSITORY, \
    GITHUB_RAW_CONTENT_URL
from tools.logging.logging_util import get_logger


def get_package_description_with_adaptation(url_or_path):
    # try with package as in configuration
    try:
        return get_package_description(url_or_path)
    except Exception:
        return get_package_description(url_or_path, True)


def get_package_description(url_or_path, try_to_adapt=False):
    package_url_or_path = str(url_or_path)
    # if its an url: download with requests.get and return text
    if get_is_url(package_url_or_path):
        if try_to_adapt:
            if not package_url_or_path.endswith("/"):
                package_url_or_path += "/"
            # if checking on github, try adding branch and file
            if GITHUB in package_url_or_path:
                package_url_or_path += f"{TENTACLES_DEFAULT_BRANCH}/{TENTACLES_PUBLIC_LIST}"
            # else try adding file
            else:
                package_url_or_path += TENTACLES_PUBLIC_LIST
        downloaded_result = json.loads(requests.get(package_url_or_path).text)
        if "error" in downloaded_result and GITHUB_BASE_URL in package_url_or_path:
            package_url_or_path = package_url_or_path.replace(GITHUB_BASE_URL, GITHUB_RAW_CONTENT_URL)
            downloaded_result = json.loads(requests.get(package_url_or_path).text)
        # add package metadata
        add_package_description_metadata(downloaded_result, package_url_or_path, True)
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
            add_package_description_metadata(read_result, package_url_or_path, False)
            return read_result


def get_is_url(string):
    return string.startswith("https://") \
        or string.startswith("http://") \
        or string.startswith("ftp://")


def add_package_description_metadata(package_description, localisation, is_url):
    to_save_loc = str(localisation)
    if localisation.endswith(TENTACLES_PUBLIC_LIST):
        to_save_loc = localisation[0:-len(TENTACLES_PUBLIC_LIST)]
        while to_save_loc.endswith("/") or to_save_loc.endswith("\\"):
            to_save_loc = to_save_loc[0:-1]
    package_description[TENTACLE_PACKAGE_DESCRIPTION] = {
        TENTACLE_PACKAGE_DESCRIPTION_LOCALISATION: to_save_loc,
        TENTACLE_PACKAGE_NAME: get_package_name(localisation, is_url),
        TENTACLE_DESCRIPTION_IS_URL: is_url
    }


def get_octobot_tentacle_public_repo(to_description_file=True):
    if to_description_file:
        return f"{GITHUB_BASE_URL}/{TENTACLES_PUBLIC_REPOSITORY}/{TENTACLES_DEFAULT_BRANCH}/{TENTACLES_PUBLIC_LIST}"
    else:
        return f"{GITHUB_BASE_URL}/{TENTACLES_PUBLIC_REPOSITORY}"


def add_package_name(module_file_content, package_name):
    return module_file_content.replace('$tentacle_description: {\n', '$tentacle_description: {\n    ' +
                                       f'"package_name": "{package_name}",\n')


def get_package_name(localisation, is_url):
    if is_url:
        github_package_name_reverse_index = -3 if localisation.endswith(".json") else -1
        return localisation.split("/")[github_package_name_reverse_index]
    else:
        local_package_name_reverse_index = -2 if localisation.endswith(".json") else -1
        separator = "/"
        if "\\" in localisation:
            separator = "\\"
        return localisation.split(separator)[local_package_name_reverse_index]


def get_package_file_content_from_url(url, as_bytes=False):
    result = requests.get(url)
    package_file = result.text

    if package_file.find("404: Not Found") != -1:
        raise Exception(f"{package_file}: {url}")

    if as_bytes:
        return result.content
    else:
        return package_file


def read_tentacles(path, description_list):
    for file_name in os.listdir(path):
        if check_path(path) and file_name.endswith(".py") \
                and file_name != PYTHON_INIT_FILE:
            with open(f"{path}/{file_name}", "r") as module:
                TentacleUtil.parse_module_file(module.read(), description_list)
        else:
            file_name = f"{path}/{file_name}"
            if os.path.isdir(file_name) and not path.startswith('.'):
                read_tentacles(file_name, description_list)


def check_path(path):
    last_path_folder = path.split("/")[-1]
    return last_path_folder in TENTACLES_INSTALL_FOLDERS


def update_config_file(config_file_path, default_file_path, classes_to_consider):

    logger = get_logger("TentaclePackageUtil")

    # initialize file content
    config_content = {}
    changed_something = False
    if os.path.isfile(config_file_path):
        with open(config_file_path, "r") as config_file_r:
            default_config_file_content = config_file_r.read()
            try:
                config_content = json.loads(default_config_file_content)
            except Exception as e:
                logger.warning(f"impossible to load content of configuration file: "
                               f"{config_file_path}: {e}")
    # take default values into account using default file
    if os.path.isfile(default_file_path):
        with open(default_file_path, "r") as default_config_file_r:
            default_config_file_content = default_config_file_r.read()
            default_config_content = json.loads(default_config_file_content)
            for key, val in default_config_content.items():
                if key not in config_content:
                    config_content[key] = val
                    changed_something = True

    classes_list = []
    # add items using their base class key (vs advances classes)
    for classes_in_config in classes_to_consider:
        changed_something = add_class_to_config_file_content(
            classes_in_config, config_content, classes_list) or changed_something

    # remove potential unnecessary items
    to_remove = []
    str_classes_list = [c.get_name() for c in classes_list]
    for key in config_content.keys():
        if key not in str_classes_list:
            to_remove.append(key)

    for key_to_remove in to_remove:
        config_content.pop(key_to_remove)
        changed_something = True

    if changed_something:
        with open(config_file_path, "w+") as config_file_w:
            config_file_w.write(json.dumps(config_content, indent=4, sort_keys=True))
            logger.info(f"{config_file_path} has been updated")
    else:
        logger.info(f"Nothing to update in {config_file_path}")


def add_class_to_config_file_content(clazz, config_file_content, classes_list, activated=False):
    from evaluator.Util.advanced_manager import AdvancedManager
    changed_something = False
    current_classes_list = AdvancedManager.create_default_types_list(clazz)
    for current_class in current_classes_list:
        if not current_class.get_name() in config_file_content:
            config_file_content[current_class.get_name()] = activated
            changed_something = True
    classes_list += current_classes_list
    return changed_something
