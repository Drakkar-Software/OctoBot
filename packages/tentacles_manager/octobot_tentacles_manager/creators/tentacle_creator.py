#  Drakkar-Software OctoBot-Tentacles-Manager
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
import os.path as path
import logging
import octobot_commons.constants
try:
    import jinja2.nativetypes as nativetypes
except ImportError:
    if octobot_commons.constants.USE_MINIMAL_LIBS:
        # mock jsonschema imports
        class NativetypesImportMock:
            class NativeEnvironment:
                def __init__(self, *args):
                    raise ImportError("jinja2 not installed")
        nativetypes = NativetypesImportMock()
    else:
        raise

import octobot_commons.logging as common_logging
import octobot_tentacles_manager.constants as constants


# TODO: remove from to .coveragerc when adapted


class TentacleCreator:
    def __init__(self, config):
        self.config = config
        self.templates = {}
        self.config_templates = {}
        self.logger = common_logging.get_logger(self.__class__.__name__)
        common_logging.set_global_logger_level(logging.INFO)

    @staticmethod
    def get_template_path(name):
        return path.join(os.path.dirname(os.path.abspath(__file__)), constants.TENTACLE_TEMPLATE_PATH,
                         f"{name}{constants.TENTACLE_TEMPLATE_PRE_EXT}{constants.TENTACLE_TEMPLATE_EXT}")

    @staticmethod
    def get_config_template_path(name):
        return path.join(os.path.dirname(os.path.abspath(__file__)), constants.TENTACLE_TEMPLATE_PATH,
                         f"{name}{constants.TENTACLE_CONFIG_TEMPLATE_PRE_EXT}{constants.TENTACLE_TEMPLATE_EXT}")

    def get_templates(self):
        return self.templates

    def get_config_templates(self):
        return self.config_templates

    def load_templates(self):
        self.templates["Description"] = open(self.get_template_path(
            constants.TENTACLE_TEMPLATE_DESCRIPTION), "r").read()
        # Todo: handle tentacle sub-types
        raise NotImplementedError("Todo: handle tentacle sub-types")
        for tentacle_type in []:
            try:
                self.templates[tentacle_type] = open(self.get_template_path(tentacle_type), "r").read()
            except FileNotFoundError:
                pass

            try:
                self.config_templates[tentacle_type] = open(self.get_config_template_path(tentacle_type), "r").read()
            except FileNotFoundError:
                pass

    def parse_commands(self, commands) -> int:
        command_help = ""
        for tentacle_type in constants.TENTACLES_FOLDERS_ARCH:
            command_help += f"- {tentacle_type}: Create a new {tentacle_type} tentacle\n"

        if commands:
            if commands[0] == "help":
                self.logger.info(f"Welcome in Tentacle Creator, commands are:\n{command_help}")
            else:
                self.load_templates()
                self.logger.warning("TENTACLE CREATOR IS IN DEVELOPMENT")
                for command in commands:
                    self.create_tentacle(command)
            return 0
        else:
            arguments_help = "-c: activates the tentacle creators."
            self.logger.error(f"Invalid arguments, arguments are: {arguments_help}")
            return 1

    def create_tentacle(self, tentacle_type):
        if tentacle_type in constants.TENTACLES_FOLDERS_ARCH:
            try:
                new_tentacle = CreatedTentacle(self.config, tentacle_type, self)
                new_tentacle.ask_description(tentacle_type)
                new_tentacle.create_file()
                new_tentacle.create_config_file()
                self.logger.info(
                    f"{new_tentacle.get_name()} tentacle successfully created in {new_tentacle.get_path()}")
            except Exception as e:
                self.logger.error(f"Tentacle creation failed : {e}")
        else:
            self.logger.warning(f"This tentacle type '{tentacle_type}' does not exist. "
                                f"Tentacle types are: {list(constants.TENTACLES_FOLDERS_ARCH.keys())}")


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

        self.config_file = self.get_config_path() if self.subtype in \
                                                     self.tentacle_creator.get_config_templates() else []
        self.logger = common_logging.get_logger(self.__class__.__name__)
        common_logging.set_global_logger_level(logging.INFO)

    def get_path(self):
        return f"{constants.TENTACLES_PATH}/{self.t_type}/{self.subtype}/{self.name}.py"

    def get_config_path(self):
        return f"{constants.TENTACLES_PATH}/{self.t_type}/{self.subtype}/" \
               f"{constants.TENTACLE_CONFIG}/{self.name}{constants.CONFIG_EXT}"

    def get_name(self):
        return self.name

    def ask_description(self, tentacle_type):
        self.name = input(f"Enter your new {self.t_type} tentacle name : ")
        while self.subtype == "":
            sub_types = constants.TENTACLES_FOLDERS_ARCH[tentacle_type]
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
            desc_template = nativetypes.NativeEnvironment().from_string(
                self.tentacle_creator.get_templates()["Description"])
            impl_template = nativetypes.NativeEnvironment().from_string(
                self.tentacle_creator.get_templates()[self.subtype])
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
                    tentacle_file.write("\n" + self.header_separator)
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
            cfg_template = nativetypes.NativeEnvironment().from_string(
                self.tentacle_creator.get_config_templates()[self.subtype])
            if not os.path.isfile(self.get_config_path()):
                with open(self.get_config_path(), "w") as config_file:
                    config_file.write(cfg_template.render()[1:])
            else:
                raise Exception("A config with this name already exists")
        except Exception:
            pass
