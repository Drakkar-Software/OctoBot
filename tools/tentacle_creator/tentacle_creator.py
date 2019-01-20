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

from jinja2.nativetypes import NativeEnvironment

from config import TENTACLE_CREATOR_PATH, TENTACLE_TEMPLATE_PATH, TOOLS_PATH, \
    TENTACLE_TEMPLATE_DESCRIPTION, TENTACLE_TEMPLATE_EXT, TENTACLE_TEMPLATE_PRE_EXT, TENTACLE_PARENTS, TENTACLE_SONS, \
    EVALUATOR_ADVANCED_FOLDER, TENTACLES_PATH, TENTACLE_CONFIG_TEMPLATE_PRE_EXT, CONFIG_FILE_EXT, \
    EVALUATOR_CONFIG_FOLDER
from tools.tentacle_manager.tentacle_util import get_tentacles_arch


class TentacleCreator:
    def __init__(self, config):
        self.tentacles_arch, _ = get_tentacles_arch()
        self.config = config
        self.templates = {}
        self.config_templates = {}
        self.logger = get_logger(self.__class__.__name__)

    @staticmethod
    def get_template_path(name):
        return f"{TOOLS_PATH}/{TENTACLE_CREATOR_PATH}/{TENTACLE_TEMPLATE_PATH}/{name,}{TENTACLE_TEMPLATE_PRE_EXT}" \
            f"{TENTACLE_TEMPLATE_EXT}"

    @staticmethod
    def get_config_template_path(name):
        return f"{TOOLS_PATH}/{TENTACLE_CREATOR_PATH}/{TENTACLE_TEMPLATE_PATH}/{name}" \
            f"{TENTACLE_CONFIG_TEMPLATE_PRE_EXT}{TENTACLE_TEMPLATE_EXT}"

    def get_templates(self):
        return self.templates

    def get_config_templates(self):
        return self.config_templates

    def load_templates(self):
        self.templates["Description"] = open(self.get_template_path(TENTACLE_TEMPLATE_DESCRIPTION), "r").read()
        for tentacle_type in TENTACLE_SONS:
            try:
                self.templates[tentacle_type] = open(self.get_template_path(tentacle_type), "r").read()
            except FileNotFoundError:
                pass

            try:
                self.config_templates[tentacle_type] = open(self.get_config_template_path(tentacle_type), "r").read()
            except FileNotFoundError:
                pass

    def parse_commands(self, commands):
        command_help = ""
        for tentacle_type in TENTACLE_PARENTS:
            command_help += f"- {tentacle_type}: Create a new {tentacle_type} tentacle\n"

        if commands:
            if commands[0] == "help":
                self.logger.info(f"Welcome in Tentacle Creator, commands are:\n{command_help}")
            else:
                self.load_templates()
                self.logger.warning("TENTACLE CREATOR IS IN DEVELOPMENT")
                for command in commands:
                    self.create_tentacle(command)
        else:
            arguments_help = "-c: activates the tentacle creator."
            self.logger.error(f"Invalid arguments, arguments are: {arguments_help}")

    def create_tentacle(self, tentacle_type):
        if tentacle_type in TENTACLE_PARENTS:
            try:
                new_tentacle = CreatedTentacle(self.config, tentacle_type, self)
                new_tentacle.ask_description(tentacle_type)
                new_tentacle.create_file()
                new_tentacle.create_config_file()
                self.logger.info("{new_tentacle.get_name()} tentacle successfully created in {new_tentacle.get_path()}")
            except Exception as e:
                self.logger.error(f"Tentacle creation failed : {e}")
        else:
            self.logger.warning(f"This tentacle type '{tentacle_type}' doesn't exist. "
                                f"Tentacle types are: {list(TENTACLE_PARENTS.keys())}")


class CreatedTentacle:
    DEFAULT_TENTACLE_VERSION = "1.0.0"

    def __init__(self, config, tentacle_type, tentacle_creator):
        self.config = config
        self.tentacle_creator = tentacle_creator

        self.header_separator = '"""\n'
        self.t_type = tentacle_type
        self.subtype = ""
        self.name = ""
        self.version = self.DEFAULT_TENTACLE_VERSION
        self.requirements = []
        self.tests = []

        self.config_file = self.get_config_path() if self.subtype in self.tentacle_creator.get_config_templates() else[]
        self.logger = get_logger(self.__class__.__name__)

    def get_path(self):
        return f"{TENTACLES_PATH}/{self.t_type}/{self.subtype}/{EVALUATOR_ADVANCED_FOLDER}/{self.name}.py"

    def get_config_path(self):
        return f"{TENTACLES_PATH}/{self.t_type}/{self.subtype}/{EVALUATOR_CONFIG_FOLDER}/{self.name}{CONFIG_FILE_EXT}"

    def get_name(self):
        return self.name

    def ask_description(self, tentacle_type):
        self.name = input(f"Enter your new {self.t_type} tentacle name : ")
        while self.subtype == "":
            sub_types = self.tentacle_creator.tentacles_arch[TENTACLES_PATH][0][tentacle_type]
            if len(sub_types) > 1:
                new_subtype = input(f"Choose your tentacle type in {sub_types} : ")
                if new_subtype in sub_types:
                    self.subtype = new_subtype
                else:
                    self.logger.warning("Invalid tentacle type")
            else:
                self.subtype = sub_types[0]

    def create_file(self):
        try:
            desc_template = NativeEnvironment().from_string(self.tentacle_creator.get_templates()["Description"])
            impl_template = NativeEnvironment().from_string(self.tentacle_creator.get_templates()[self.subtype])
            if not os.path.isfile(self.get_path()):
                with open(self.get_path(), "w") as tentacle_file:
                    tentacle_file.write(self.header_separator)
                    tentacle_file.write(desc_template.render(name=self.name,
                                                             big_name=self.name.title(),
                                                             t_type=self.t_type,
                                                             subtype=self.subtype,
                                                             version=self.version,
                                                             requirements=self.requirements,
                                                             tests=self.tests,
                                                             config=self.config_file))
                    tentacle_file.write("\n"+self.header_separator)
                    tentacle_file.write(impl_template.render(name=self.name,
                                                             big_name=self.name.title(),
                                                             t_type=self.t_type,
                                                             subtype=self.subtype,
                                                             version=self.version,
                                                             requirements=self.requirements,
                                                             tests=self.tests,
                                                             config=self.config_file))

                # TODO add __init__.py management
            else:
                raise Exception("A tentacle with this name already exists")
        except Exception as e:
            raise e

    def create_config_file(self):
        try:
            cfg_template = NativeEnvironment().from_string(self.tentacle_creator.get_config_templates()[self.subtype])
            if not os.path.isfile(self.get_config_path()):
                with open(self.get_config_path(), "w") as config_file:
                    config_file.write(cfg_template.render()[1:])
            else:
                raise Exception("A config with this name already exists")
        except Exception:
            pass
