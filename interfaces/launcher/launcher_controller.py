import glob
import json
import logging
import os
import subprocess
from distutils.version import LooseVersion
from subprocess import PIPE

import requests

from config.cst import CONFIG_FILE, PROJECT_NAME, GITHUB_API_CONTENT_URL, GITHUB_REPOSITORY, GITHUB_RAW_CONTENT_URL, \
    VERSION_DEV_PHASE, DEFAULT_CONFIG_FILE, LOGGING_CONFIG_FILE, DeliveryPlatformsName, TENTACLES_PATH

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

LIB_FILES_DOWNLOAD_PROGRESS_SIZE = 5
CREATE_FOLDERS_PROGRESS_SIZE = 5
BINARY_DOWNLOAD_PROGRESS_SIZE = 75
TENTACLES_UPDATE_INSTALL_PROGRESS_SIZE = 15


class Launcher:
    def __init__(self, inst_app):
        self.installer_app = inst_app

        self.create_environment()
        binary_path = self.update_binary()
        self.update_tentacles(binary_path)

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

        if self.installer_app:
            self.installer_app.inc_progress(LIB_FILES_DOWNLOAD_PROGRESS_SIZE)

        # create folders
        for folder in FOLDERS_TO_CREATE:
            if not os.path.exists(folder) and folder:
                os.makedirs(folder)

        if self.installer_app:
            self.installer_app.inc_progress(CREATE_FOLDERS_PROGRESS_SIZE)

        logging.info(f"Your {PROJECT_NAME} environment is ready !")

    def update_binary(self):
        # parse latest release
        try:
            logging.info(f"{PROJECT_NAME} is checking for updates...")
            latest_release_data = self.get_latest_release_data()

            # try to found in current folder binary
            binary_path = self.get_local_bot_binary()

            # if current octobot binary found
            if binary_path:
                logging.info(f"{PROJECT_NAME} installation found, analyzing...")

                last_release_version = latest_release_data["tag_name"]
                current_bot_version = self.execute_command_on_current_bot(binary_path, ["--version"])

                try:
                    check_new_version = LooseVersion(current_bot_version) < LooseVersion(last_release_version)
                except AttributeError:
                    check_new_version = False

                if check_new_version:
                    logging.info(f"Upgrading {PROJECT_NAME} : from {current_bot_version} to {last_release_version}...")
                    return self.download_binary(latest_release_data, replace=True)
                else:
                    logging.info(f"Nothing to do : {PROJECT_NAME} is up to date")
                    if self.installer_app:
                        self.installer_app.inc_progress(BINARY_DOWNLOAD_PROGRESS_SIZE)
                    return binary_path
            else:
                return self.download_binary(latest_release_data)
        except Exception as e:
            logging.exception(f"Failed to download latest release data : {e}")

    @staticmethod
    def get_local_bot_binary():
        # try to found in current folder binary
        octobot_binaries = glob.glob(f'{PROJECT_NAME}*')

        try:
            octobot_binary = next(iter(octobot_binaries))
        except Exception:
            octobot_binary = None

        if octobot_binary and os.name == 'posix':
            octobot_binary = "./" + octobot_binary

        return octobot_binary

    @staticmethod
    def get_latest_release_data():
        return json.loads(requests.get(GITHUB_LATEST_RELEASE_URL).text)

    @staticmethod
    def execute_command_on_current_bot(binary_path, commands):
        try:
            cmd = [f"{binary_path}"] + commands
            return subprocess.Popen(cmd, stdout=PIPE).stdout.read().rstrip().decode()
        except PermissionError:
            logging.exception(f"Failed to run bot with command {commands} : {e}")

    @staticmethod
    def execute_command_on_detached_bot(binary_path=None, commands=None):
        try:
            if not binary_path:
                binary_path = Launcher.get_local_bot_binary()

            cmd = [f"{binary_path}"] + (commands if commands else [])
            return subprocess.Popen(cmd)
        except Exception as e:
            logging.exception(f"Failed to run detached bot with command {commands} : {e}")
            return None

    @staticmethod
    def get_asset_from_release_data(latest_release_data):
        os_name = None

        # windows
        if os.name == 'nt':
            os_name = DeliveryPlatformsName.WINDOWS

        # linux
        if os.name == 'posix':
            os_name = DeliveryPlatformsName.LINUX

        # mac
        if os.name == 'mac':
            os_name = DeliveryPlatformsName.MAC

        # search for corresponding release
        for asset in latest_release_data["assets"]:
            asset_name, _ = os.path.splitext(asset["name"])
            if asset_name == f"{PROJECT_NAME}_{os_name.value}":
                return asset

        return None

    def download_binary(self, latest_release_data, replace=False):
        binary = self.get_asset_from_release_data(latest_release_data)

        final_size = binary["size"]
        increment = (BINARY_DOWNLOAD_PROGRESS_SIZE / (final_size / 1024))

        r = requests.get(binary["browser_download_url"], stream=True)

        binary_name, binary_ext = os.path.splitext(binary["name"])
        path = f"{PROJECT_NAME}{binary_ext}"

        if r.status_code == 200:

            if replace and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    logging.error(f"Can't remove old version binary : {e}")

            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
                    if self.installer_app:
                        self.installer_app.inc_progress(increment)

        return path

    def update_tentacles(self, binary_path):
        # if install required
        if not os.path.exists(TENTACLES_PATH):
            self.execute_command_on_current_bot(binary_path, ["-p", "install", "all"])
            logging.info(f"Tentacles : all default tentacles has been installed.")

        # update
        else:
            self.execute_command_on_current_bot(binary_path, ["-p", "update", "all"])
            logging.info(f"Tentacles : all default tentacles has been updated.")

        if self.installer_app:
            self.installer_app.inc_progress(TENTACLES_UPDATE_INSTALL_PROGRESS_SIZE, to_max=True)
