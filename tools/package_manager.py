import json
import logging

import requests

from config.cst import PACKAGES_PUBLIC_LIST, PACKAGES_DEFAULT_BRANCH, PACKAGES_PUBLIC_REPOSITORY, \
    GITHUB_RAW_CONTENT_URL, CONFIG_EVALUATOR


class PackageManager:
    def __init__(self, config):
        self.config = config
        self.package_list = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def update_list(self):
        package_list_url = "{0}/{1}/{2}/{3}".format(GITHUB_RAW_CONTENT_URL,
                                                    PACKAGES_PUBLIC_REPOSITORY,
                                                    PACKAGES_DEFAULT_BRANCH,
                                                    PACKAGES_PUBLIC_LIST)

        self.package_list = json.loads(requests.get(package_list_url).text)

    def install_package(self, package_name):
        package_type = self.package_list[package_name]["type"]
        package_url = "{0}/{1}/{2}/{3}/{4}.py".format(GITHUB_RAW_CONTENT_URL,
                                                      PACKAGES_PUBLIC_REPOSITORY,
                                                      PACKAGES_DEFAULT_BRANCH,
                                                      package_type,
                                                      package_name)
        package_file = requests.get(package_url).text

        # Install package in evaluator
        with open("{0}/{1}/{2}.py".format(CONFIG_EVALUATOR, package_type, package_name), "w") as installed_package:
            installed_package.write(package_file)

        # Update local __init__
        new_line_in_init = "from .{0} import *\n".format(package_name)

        init_file = "{0}/{1}/__init__.py".format(CONFIG_EVALUATOR, package_type)
        with open(init_file, "r") as init_file_r:
            init_content = init_file_r.read()

        # check if line already exists
        if init_content and init_content.find(new_line_in_init) == -1:
            with open(init_file, "w") as init_file_w:

                # add new package to init
                init_file_w.write(init_content + new_line_in_init)

        self.logger.info("{0} installed successfully".format(package_name))

    def parse_commands(self, commands):
        self.update_list()
        if len(commands) > 0:
            if commands[0] == "install":

                if commands[1] and commands[1] == "all":
                    for package in self.package_list:
                        self.install_package(package)
                else:
                    commands.pop(0)
                    for component in commands:
                        if component in self.package_list:
                            self.install_package(component)
                        else:
                            self.logger.warning("Cannot find installation for package '{0}'".format(component))
