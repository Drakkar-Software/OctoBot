import glob
import json
import logging
import os

import requests

from config.cst import CONFIG_FILE, PROJECT_NAME, GITHUB_API_CONTENT_URL, GITHUB_REPOSITORY, GITHUB_RAW_CONTENT_URL, \
    VERSION_DEV_PHASE, DEFAULT_CONFIG_FILE, LOGGING_CONFIG_FILE

FOLDERS_TO_CREATE = ["logs"]
FILES_TO_DOWNLOAD = [
    (
        f"{GITHUB_RAW_CONTENT_URL}/cjhutto/vaderSentiment/master/vaderSentiment/emoji_utf8_lexicon.txt",
        "vaderSentiment/emoji_utf8_lexicon.txt"),
    (
        f"{GITHUB_RAW_CONTENT_URL}/cjhutto/vaderSentiment/master/vaderSentiment/vader_lexicon.txt",
        "vaderSentiment/vader_lexicon.txt"),
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{DEFAULT_CONFIG_FILE}",
        CONFIG_FILE
    ),
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{LOGGING_CONFIG_FILE}",
        LOGGING_CONFIG_FILE
    )
]

GITHUB_LATEST_RELEASE_URL = f"{GITHUB_API_CONTENT_URL}/repos/{GITHUB_REPOSITORY}/releases/latest"


class Installer:
    def __init__(self, inst_app):
        self.installer_app = inst_app

        self.create_environment()
        self.update_binary()
        self.update_tentacles()

    def create_environment(self):
        logging.info(f"{PROJECT_NAME} is checking your environment...")
        # download files
        for file_to_dl in FILES_TO_DOWNLOAD:
            file_content = requests.get(file_to_dl[0]).text
            directory = os.path.dirname(file_to_dl[1])

            if not os.path.exists(directory) and directory:
                os.makedirs(directory)

            file_name = file_to_dl[1]
            if not os.path.isfile(file_name) and file_name:
                with open(file_name, "w") as new_file_from_dl:
                    new_file_from_dl.write(file_content)

        self.installer_app.inc_progress(5)

        # create folders
        for folder in FOLDERS_TO_CREATE:
            if not os.path.exists(folder) and folder:
                os.makedirs(folder)

        self.installer_app.inc_progress(5)

        logging.info(f"Your {PROJECT_NAME} environment is ready !")

    def update_binary(self):
        # parse latest release
        try:
            logging.info(f"{PROJECT_NAME} is checking for updates...")
            latest_release_data = json.loads(requests.get(GITHUB_LATEST_RELEASE_URL).text)
            latest_version = latest_release_data["tag_name"]

            # try to found in current folder binary
            octobot_binaries = glob.glob(f'{PROJECT_NAME}*')

            # if current octobot binary found
            if octobot_binaries:
                logging.info(f"{PROJECT_NAME} installation found, analyzing...")

                # TODO temp --> check if current version is <
                self.download_binary(latest_release_data)
            else:
                self.download_binary(latest_release_data)

            pass
        except Exception as e:
            logging.error(f"Failed to download latest release data : {e}")

    def download_binary(self, latest_release_data):
        # TEMP Choose binary
        binary = None

        # windows
        if os.name == 'nt':
            binary = latest_release_data["assets"][1]

        # linux
        if os.name == 'posix':
            binary = latest_release_data["assets"][0]

        # mac
        if os.name == 'mac':
            pass

        final_size = binary["size"]
        binary_progress_importance = 75
        increment = (binary_progress_importance / (final_size / 1024))

        r = requests.get(binary["browser_download_url"], stream=True)

        binary_name, binary_ext = os.path.splitext(binary["name"])
        path = f"{PROJECT_NAME}{binary_ext}"

        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
                    self.installer_app.inc_progress(increment)

    def update_tentacles(self):
        # TODO : call current binary "-p install all"
        # os.execl("", ["-p", "install", "all"])
        self.installer_app.inc_progress(5, to_max=True)
