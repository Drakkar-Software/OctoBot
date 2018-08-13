import argparse
import importlib
import logging

from config.cst import GITHUB_RAW_CONTENT_URL, GITHUB_REPOSITORY, LAUNCHER_PATH

logging.basicConfig(level=logging.INFO)

# should have VERSION_DEV_PHASE
LAUNCHER_URL = f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/dev/{LAUNCHER_PATH}"

LAUNCHER_FILES = ["launcher_app.py", "launcher_controller.py"]


def update_launcher():
    logging.info("Updating launcher...")
    for file in LAUNCHER_FILES:
        create_environment_file(f"{LAUNCHER_URL}/{file}", f"{LAUNCHER_PATH}/{file}")


try:
    from interfaces.launcher import launcher_app, launcher_controller, create_environment_file
except ImportError:
    update_launcher()
    try:
        # importlib.import_module("interfaces.launcher")
        from interfaces.launcher import launcher_app, launcher_controller, create_environment_file
    except ImportError as e:
        logging.error(f"Failed to start launcher : {e}")


if __name__ == '__main__':
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
        installer_app = launcher_app.LauncherApp()
        installer = launcher_controller.Launcher(installer_app)
