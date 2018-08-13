import argparse
import importlib
import logging

logging.basicConfig(level=logging.INFO)

try:
    from interfaces.launcher import *
except ImportError:
    update_launcher()
    try:
        importlib.import_module("interfaces.launcher")
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
    start_launcher(args)
