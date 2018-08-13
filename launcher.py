import argparse
import importlib
import logging

from config.cst import GITHUB_RAW_CONTENT_URL, GITHUB_REPOSITORY, LAUNCHER_FILE, LAUNCHER_PATH
from interfaces.launcher import create_environment_file
from interfaces.launcher.launcher_app import LauncherApp

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        from interfaces.launcher import launcher_controller
    except ImportError:
        # should have VERSION_DEV_PHASE
        logging.info("Installing launcher...")
        launcher_url = f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/dev/{LAUNCHER_PATH}/{LAUNCHER_FILE}"
        create_environment_file(launcher_url, LAUNCHER_FILE)
        try:
            importlib.import_module("launcher")
        except ImportError as e:
            logging.error(f"Failed to start launcher : {e}")

    parser = argparse.ArgumentParser(description='OctoBot - Launcher')
    parser.add_argument('-v', '--version', help='show OctoBot Launcher current version',
                        action='store_true')
    parser.add_argument('-u', '--update', help='update OctoBot with the latest version available',
                        action='store_true')

    parser.add_argument('-l', '--update_launcher', help='update OctoBot Launcher with the latest version available',
                        action='store_true')

    args = parser.parse_args()

    if args.version:
        print(launcher_controller.Launcher.get_version())
    elif args.update:
        pass
    elif args.update_launcher:
        pass
    else:
        installer_app = LauncherApp()
        installer = launcher_controller.Launcher(installer_app)
