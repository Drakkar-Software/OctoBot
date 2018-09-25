import glob
import json
import logging
import os
import subprocess
import urllib.request
from distutils.version import LooseVersion
from subprocess import PIPE
from tkinter.messagebox import WARNING

import requests

from config.cst import CONFIG_FILE, PROJECT_NAME, GITHUB_API_CONTENT_URL, GITHUB_REPOSITORY, GITHUB_RAW_CONTENT_URL, \
    VERSION_DEV_PHASE, DEFAULT_CONFIG_FILE, LOGGING_CONFIG_FILE, DeliveryPlatformsName, TENTACLES_PATH, \
    CONFIG_DEFAULT_EVALUATOR_FILE, CONFIG_DEFAULT_TRADING_FILE, CONFIG_INTERFACES, CONFIG_INTERFACES_WEB, \
    OCTOBOT_BACKGROUND_IMAGE, OCTOBOT_ICON

FOLDERS_TO_CREATE = ["logs", "backtesting/collector/data"]
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
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{CONFIG_DEFAULT_EVALUATOR_FILE}",
        CONFIG_DEFAULT_EVALUATOR_FILE
    ),
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{CONFIG_DEFAULT_TRADING_FILE}",
        CONFIG_DEFAULT_TRADING_FILE
    )
]
IMAGES_TO_DOWNLOAD = [
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{LOGGING_CONFIG_FILE}",
        LOGGING_CONFIG_FILE
    ),
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{CONFIG_INTERFACES}/{CONFIG_INTERFACES_WEB}"
        f"/{OCTOBOT_BACKGROUND_IMAGE}",
        f"{CONFIG_INTERFACES}/{CONFIG_INTERFACES_WEB}/{OCTOBOT_BACKGROUND_IMAGE}"
    ),
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{CONFIG_INTERFACES}/{CONFIG_INTERFACES_WEB}"
        f"/{OCTOBOT_ICON}",
        f"{CONFIG_INTERFACES}/{CONFIG_INTERFACES_WEB}/{OCTOBOT_ICON}"
    )
]

GITHUB_LATEST_RELEASE_URL = f"{GITHUB_API_CONTENT_URL}/repos/{GITHUB_REPOSITORY}/releases/latest"

LIB_FILES_DOWNLOAD_PROGRESS_SIZE = 5
CREATE_FOLDERS_PROGRESS_SIZE = 5
BINARY_DOWNLOAD_PROGRESS_SIZE = 75
TENTACLES_UPDATE_INSTALL_PROGRESS_SIZE = 15


class Launcher:
    def __init__(self, inst_app):
        self.launcher_app = inst_app

        self.create_environment()

        binary_path = self.update_binary()

        # give binary execution rights if necessary
        if binary_path:
            self.binary_execution_rights(binary_path)

        # if update tentacles
        if binary_path:
            self.update_tentacles(binary_path)
        else:
            logging.error(f"No {PROJECT_NAME} found to update tentacles.")

    @staticmethod
    def _ensure_directory(file_path):
        directory = os.path.dirname(file_path)

        if not os.path.exists(directory) and directory:
            os.makedirs(directory)

    @staticmethod
    def ensure_minimum_environment():
        need_to_create_environment = False
        try:
            for file_to_dl in IMAGES_TO_DOWNLOAD:

                Launcher._ensure_directory(file_to_dl[1])

                file_name = file_to_dl[1]
                if not os.path.isfile(file_name) and file_name:
                    if not need_to_create_environment:
                        print("Creating minimum launcher environment...")
                    need_to_create_environment = True
                    urllib.request.urlretrieve(file_to_dl[0], file_name)

            for folder in FOLDERS_TO_CREATE:
                if not os.path.exists(folder) and folder:
                    os.makedirs(folder)
        except Exception as e:
            print(f"Error when creating minimum launcher environment: {e} this should not prevent launcher "
                  f"from working.")

    def create_environment(self):
        self.launcher_app.inc_progress(0, to_min=True)
        logging.info(f"{PROJECT_NAME} is checking your environment...")

        # download files
        for file_to_dl in FILES_TO_DOWNLOAD:

            Launcher._ensure_directory(file_to_dl[1])

            file_name = file_to_dl[1]
            if not os.path.isfile(file_name) and file_name:
                with open(file_name, "wb") as new_file_from_dl:
                    file_content = requests.get(file_to_dl[0]).text
                    new_file_from_dl.write(file_content.encode())

        self.launcher_app.window.update()

        if self.launcher_app:
            self.launcher_app.inc_progress(LIB_FILES_DOWNLOAD_PROGRESS_SIZE)

        if self.launcher_app:
            self.launcher_app.inc_progress(CREATE_FOLDERS_PROGRESS_SIZE)

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
                current_bot_version = self.get_current_bot_version(binary_path)

                try:
                    check_new_version = LooseVersion(current_bot_version) < LooseVersion(last_release_version)
                except AttributeError:
                    check_new_version = False

                if check_new_version:
                    logging.info(f"Upgrading {PROJECT_NAME} : from {current_bot_version} to {last_release_version}...")
                    return self.download_binary(latest_release_data, replace=True)
                else:
                    logging.info(f"Nothing to do : {PROJECT_NAME} is up to date")
                    if self.launcher_app:
                        self.launcher_app.inc_progress(BINARY_DOWNLOAD_PROGRESS_SIZE)
                    return binary_path
            else:
                return self.download_binary(latest_release_data)
        except Exception as e:
            logging.exception(f"Failed to download latest release data : {e}")

    @staticmethod
    def get_current_bot_version(binary_path=None):
        if not binary_path:
            binary_path = Launcher.get_local_bot_binary()
        return Launcher.execute_command_on_current_bot(binary_path, ["--version"])

    @staticmethod
    def get_local_bot_binary():
        binary = None

        try:
            # try to found in current folder binary
            if os.name == 'posix':
                binary = "./" + next(iter(glob.glob(f'{PROJECT_NAME}*')))

            elif os.name == 'nt':
                binary = next(iter(glob.glob(f'{PROJECT_NAME}*.exe')))

            elif os.name == 'mac':
                pass
        except StopIteration:
            binary = None

        return binary

    @staticmethod
    def get_current_server_version(latest_release_data=None):
        if not latest_release_data:
            latest_release_data = Launcher.get_latest_release_data()
        return latest_release_data["tag_name"]

    @staticmethod
    def get_latest_release_data():
        return json.loads(requests.get(GITHUB_LATEST_RELEASE_URL).text)

    @staticmethod
    def execute_command_on_current_bot(binary_path, commands):
        try:
            cmd = [f"{binary_path}"] + commands
            return subprocess.Popen(cmd, stdout=PIPE).stdout.read().rstrip().decode()
        except PermissionError as e:
            logging.error(f"Failed to run bot with command {commands} : {e}")
        except FileNotFoundError as e:
            logging.error(f"Can't find a valid binary")

    @staticmethod
    def execute_command_on_detached_bot(binary_path=None, commands=None):
        try:
            if not binary_path:
                binary_path = Launcher.get_local_bot_binary()

            cmd = [f"{binary_path}"] + (commands if commands else [])
            return subprocess.Popen(cmd)
        except Exception as e:
            logging.error(f"Failed to run detached bot with command {commands} : {e}")
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
            if f"{PROJECT_NAME}_{os_name.value}" in asset_name:
                return asset
        return None

    def download_binary(self, latest_release_data, replace=False):
        binary = self.get_asset_from_release_data(latest_release_data)

        if binary:
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
                        if self.launcher_app:
                            self.launcher_app.inc_progress(increment)

            return path
        else:
            logging.error("Release not found on server")
            return None

    def update_tentacles(self, binary_path):
        # if install required
        if not os.path.exists(TENTACLES_PATH):
            self.execute_command_on_current_bot(binary_path, ["-p", "install", "all"])
            logging.info(f"Tentacles : all default tentacles have been installed.")

        # update
        else:
            self.execute_command_on_current_bot(binary_path, ["-p", "update", "all"])
            logging.info(f"Tentacles : all default tentacles have been updated.")

        if self.launcher_app:
            self.launcher_app.inc_progress(TENTACLES_UPDATE_INSTALL_PROGRESS_SIZE, to_max=True)

    def binary_execution_rights(self, binary_path):
        if os.name == 'posix':

            try:
                rights_process = subprocess.Popen(["chmod", "+x", binary_path])
            except Exception as e:
                logging.error(f"Failed to give execution rights to {binary_path} : {e}")
                rights_process = None

            if not rights_process:
                # show message if user has to type the command
                message = f"{PROJECT_NAME} binary need execution rights, " \
                          f"please type in a command line 'sudo chmod +x ./{PROJECT_NAME}'"
                logging.warning(message)
                if self.launcher_app:
                    self.launcher_app.show_alert(f"{message} and then press OK", bitmap=WARNING)
