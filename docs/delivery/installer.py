import logging
import os

import requests

from config.cst import CONFIG_FILE, PROJECT_NAME

FOLDERS_TO_CREATE = ["logs"]
FILES_TO_DOWNLOAD = [(
    "https://raw.githubusercontent.com/cjhutto/vaderSentiment/master/vaderSentiment/emoji_utf8_lexicon.txt",
    "vaderSentiment/emoji_utf8_lexicon.txt"),
    (
        "https://raw.githubusercontent.com/cjhutto/vaderSentiment/master/vaderSentiment/vader_lexicon.txt",
        "vaderSentiment/vader_lexicon.txt"),
    ("https://github.com/Drakkar-Software/OctoBot/blob/beta/config/default_config.json",
     CONFIG_FILE)]

if __name__ == '__main__':
    logger = logging.getLogger(f"{PROJECT_NAME} Installer")

    # download files
    for file_to_dl in FILES_TO_DOWNLOAD:
        file_content = requests.get(file_to_dl[0]).text
        directory = os.path.dirname(file_to_dl[1])

        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_to_dl[1], "w") as new_file_from_dl:
            new_file_from_dl.write(file_content)

    # create folders
    for folder in FOLDERS_TO_CREATE:
        if not os.path.exists(folder):
            os.makedirs(folder)

