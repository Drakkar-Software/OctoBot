import os

import requests

from config.cst import GITHUB_RAW_CONTENT_URL, GITHUB_REPOSITORY, LAUNCHER_PATH

# should have VERSION_DEV_PHASE
from interfaces.launcher.launcher_app import LauncherApp
from interfaces.launcher.launcher_controller import Launcher

LAUNCHER_URL = f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/dev/{LAUNCHER_PATH}"

LAUNCHER_FILES = ["launcher_app.py", "launcher_controller.py"]

LAUNCHER_VERSION = "1.0.0"


def update_launcher():
    logging.info("Updating launcher...")
    for file in LAUNCHER_FILES:
        create_launcher_files(f"{LAUNCHER_URL}/{file}", f"{LAUNCHER_PATH}/{file}")


def create_launcher_files(file_to_dl, result_file_path):
    file_content = requests.get(file_to_dl).text
    directory = os.path.dirname(result_file_path)

    if not os.path.exists(directory) and directory:
        os.makedirs(directory)

    file_name = result_file_path
    if not os.path.isfile(file_name) and file_name:
        with open(file_name, "w") as new_file_from_dl:
            new_file_from_dl.write(file_content)


def start_launcher(args):
    if args.version:
        print(LAUNCHER_VERSION)
    elif args.update:
        pass
    elif args.update_launcher:
        pass
    else:
        installer_app = LauncherApp()
        installer = Launcher(installer_app)
