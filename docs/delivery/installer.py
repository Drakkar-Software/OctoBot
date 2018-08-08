import argparse
import os

import requests

from config.cst import DEFAULT_CONFIG_FILE, CONFIG_FILE

FOLDERS_TO_CREATE = ["logs"]
FILES_TO_DOWNLOAD = [(
                     "https://raw.githubusercontent.com/cjhutto/vaderSentiment/master/vaderSentiment/emoji_utf8_lexicon.txt",
                     "vaderSentiment/emoji_utf8_lexicon.txt"),
                     (
                     "https://raw.githubusercontent.com/cjhutto/vaderSentiment/master/vaderSentiment/vader_lexicon.txt",
                     "vaderSentiment/vader_lexicon.txt")]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OctoBot-Installer-Updater')
    parser.add_argument('-u', '--update', help='update OctoBot with the latest version available',
                        action='store_true')

    args = parser.parse_args()
    if args.update:
        pass
    else:
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

        # config
        if not os.path.isfile(CONFIG_FILE):
            default_config_content = None

            with open(DEFAULT_CONFIG_FILE, "r") as default_config_file:
                default_config_content = default_config_file.read()

            if default_config_content:
                with open(CONFIG_FILE, "w") as new_config_file:
                    new_config_file.write(default_config_content)
