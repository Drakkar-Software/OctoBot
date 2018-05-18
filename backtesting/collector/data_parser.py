import json
import os

from config.cst import CONFIG_DATA_COLLECTOR_PATH


class DataCollectorParser:
    @staticmethod
    def parse(file):
        if os.path.isfile(CONFIG_DATA_COLLECTOR_PATH + file):
            with open(CONFIG_DATA_COLLECTOR_PATH + file) as file_to_parse:
                file_content = json.loads(file_to_parse.read())
        else:
            with open(file) as file_to_parse:
                file_content = json.loads(file_to_parse.read())
        return file_content
