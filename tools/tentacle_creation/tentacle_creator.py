import logging

from config.cst import TENTACLE_TYPES, TENTACLES_PATH


class TentacleCreator:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_commands(self, commands):
        command_help = "- strategy: Create a new strategy tentacle"

        if commands:
            if commands[0] == "help":
                self.logger.info("Welcome in Tentacle Manager, commands are:\n{0}".format(command_help))
            else:
                self.logger.error("TENTACLE CREATOR IS IN DEVELOPMENT")
                # for command in commands:
                #     self.create_tentacle(command)
        else:
            arguments_help = "-c: activates the tentacle creator."
            self.logger.error("Invalid arguments, arguments are: {0}".format(arguments_help))

    def create_tentacle(self, tentacle_type):
        if tentacle_type in TENTACLE_TYPES:
            try:
                new_tentacle = CreatedTentacle(self.config, tentacle_type)
                new_tentacle.ask_description()
                new_tentacle.create_file()
                self.logger.info("{0} tentacle successfully created in {1}".format(new_tentacle.get_name(),
                                                                                   new_tentacle.get_path()))
            except Exception as e:
                self.logger.error("Tentacle creation failed : {0}".format(e))
        else:
            self.logger.warning("This tentacle type doesn't exist")


class CreatedTentacle:
    DEFAULT_TENTACLE_VERSION = "1.0.0"
    TENTACLE_DESCRIPTION_SEPARATOR = '"""'

    def __init__(self, config, tentacle_type):
        self.config = config

        self.t_type = "#TODO"
        self.subtype = tentacle_type
        self.name = ""
        self.version = self.DEFAULT_TENTACLE_VERSION
        self.requirements = []
        self.tests = []

    def get_path(self):
        return "{0}/{1}/{2}/{3}.py".format(TENTACLES_PATH, self.t_type, self.subtype, self.name)

    def get_file_description(self):
        return 'OctoBot Tentacle \n\
                $tentacle_description: { \n\
                    "name": "{0}", \n\
                    "type": "{1}", \n\
                    "subtype": "{2}", \n\
                    "version": "{3}", \n\
                    "requirements": {4}, \n\
                    "tests": {5} \n\
                }'.format(self.name,
                          self.t_type,
                          self.subtype,
                          self.version,
                          self.requirements,
                          self.tests)

    def get_name(self):
        return self.name

    def ask_description(self):
        self.name = input("Enter your new {0} tentacle name".format(self.subtype))

    def create_file(self):
        with open(self.get_path()) as tentacle_file:
            tentacle_file.write(self.TENTACLE_DESCRIPTION_SEPARATOR)
            tentacle_file.write(self.get_file_description())
            tentacle_file.write(self.TENTACLE_DESCRIPTION_SEPARATOR)
