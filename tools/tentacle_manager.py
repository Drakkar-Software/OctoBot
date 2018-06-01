import json
import logging
import os

import requests

from config.cst import TENTACLES_PUBLIC_LIST, TENTACLES_DEFAULT_BRANCH, TENTACLES_PUBLIC_REPOSITORY, TENTACLE_DESCRIPTION,\
    GITHUB_RAW_CONTENT_URL, CONFIG_EVALUATOR, EVALUATOR_DEFAULT_FOLDER, CONFIG_TENTACLES_KEY, GITHUB_BASE_URL, GITHUB, \
    TENTACLE_DESCRIPTION_LOCALISATION, TENTACLE_DESCRIPTION_IS_URL, EVALUATOR_ADVANCED_FOLDER


class TentacleManager:
    def __init__(self, config):
        self.config = config
        self.default_package = None
        self.advanced_package_list = []
        self.logger = logging.getLogger(self.__class__.__name__)

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

    def _apply_module(self, module_type, module_name, module_version, module_file, target_folder):
        file_dir = "{0}/{1}/{2}".format(CONFIG_EVALUATOR, module_type, target_folder)

        # Install package in evaluator
        with open("{0}/{1}.py".format(file_dir, module_name), "w") as installed_package:
            installed_package.write(module_file)

        # Update local __init__
        new_line_in_init = "from .{0} import *\n".format(module_name)
        init_content = ""
        init_file = "{0}/{1}/{2}/__init__.py".format(CONFIG_EVALUATOR, module_type, target_folder)

        if os.path.isfile(init_file):
            with open(init_file, "r") as init_file_r:
                init_content = init_file_r.read()

        # check if line already exists
        if init_content.find(new_line_in_init) == -1:
            with open(init_file, "w") as init_file_w:
                # add new package to init
                init_file_w.write(init_content + new_line_in_init)

        self.logger.info("{0} {1} successfully installed in: {2}"
                         .format(module_name, module_version, file_dir))

    def install_module(self, package, module_name, package_localisation, is_url, target_folder):
        package_type = package[module_name]["type"]
        module_loc = "{0}/{1}/{2}.py".format(package_localisation, package_type, module_name)
        module_version = package[module_name]["version"]

        if is_url:
            module_file = self._get_package_from_url(module_loc)
        else:
            with open(module_loc, "r") as module:
                module_file = module.read()

        self._apply_module(package_type, module_name, module_version, module_file, target_folder)

    def _try_to_install_package(self, package, target_folder):
        package_description = package[TENTACLE_DESCRIPTION]
        package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
        is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
        for module in package:
            try:
                if module != TENTACLE_DESCRIPTION:
                    self.install_module(package, module, package_localisation, is_url, target_folder)
            except Exception as e:
                self.logger.error("Installation failed for module '{0}' ({1})".format(module, e))

    @staticmethod
    def parse_version(version):
        return int(version.replace(".", ""))

    def parse_commands(self, commands):
        self.update_list()
        if commands:
            if commands[0] == "install":

                if commands[1] == "all":
                    self._try_to_install_package(self.default_package, EVALUATOR_DEFAULT_FOLDER)
                    for package in self.advanced_package_list:
                        self._try_to_install_package(package, EVALUATOR_ADVANCED_FOLDER)
                else:
                    commands.pop(0)
                    for component in commands:
                        if component in self.default_package:
                            package_description = self.default_package[TENTACLE_DESCRIPTION]
                            package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
                            is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
                            try:
                                self.install_module(self.default_package, component, package_localisation, is_url,
                                                    EVALUATOR_DEFAULT_FOLDER)
                            except Exception:
                                self.logger.error("Installation failed for module '{0}'".format(component))
                        else:
                            found = False
                            for advanced_package in self.advanced_package_list:
                                if component in advanced_package:
                                    found = True
                                    package_description = advanced_package[TENTACLE_DESCRIPTION]
                                    package_localisation = package_description[TENTACLE_DESCRIPTION_LOCALISATION]
                                    is_url = package_description[TENTACLE_DESCRIPTION_IS_URL]
                                    try:
                                        self.install_module(advanced_package, component, package_localisation, is_url,
                                                            EVALUATOR_ADVANCED_FOLDER)
                                        break
                                    except Exception:
                                        self.logger.error("Installation failed for module '{0}'".format(component))
                            if not found:
                                self.logger.error("Cannot find installation for module '{0}'".format(component))

            if commands[0] == "update":
                if commands[1] == "all":
                    pass
                else:
                    commands.pop(0)
