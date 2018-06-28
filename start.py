import argparse
import logging
import sys
import traceback
from logging.config import fileConfig
from time import sleep

from config.config import load_config
from config.cst import *
from tools.commands import Commands
from interfaces.telegram.bot import TelegramApp
from services import WebService


def _log_uncaught_exceptions(ex_cls, ex, tb):
    logging.exception(''.join(traceback.format_tb(tb)))
    logging.exception('{0}: {1}'.format(ex_cls, ex))


def start_octobot(starting_args):
    if starting_args.pause_time is not None:
        sleep(starting_args.pause_time)

    fileConfig('config/logging_config.ini')

    logger = logging.getLogger("OctoBot Launcher")

    # Force new log file creation not to log at the previous one's end.
    logger.parent.handlers[1].doRollover()

    sys.excepthook = _log_uncaught_exceptions

    # Version
    logger.info("Version : {0}".format(LONG_VERSION))

    # Test update
    Commands.check_bot_update(logger)

    logger.info("Loading config files...")
    config = load_config()

    # Handle utility methods before bot initializing if possible
    if starting_args.packager:
        Commands.package_manager(config, starting_args.packager)

    elif starting_args.creator:
        Commands.tentacle_creator(config, starting_args.creator)

    elif starting_args.update:
        Commands.update(logger)

    else:
        # In those cases load OctoBot
        from octobot import OctoBot

        config[CONFIG_EVALUATOR] = load_config(CONFIG_EVALUATOR_FILE_PATH, False)

        TelegramApp.enable(config, starting_args.telegram)

        WebService.enable(config, starting_args.web)

        bot = OctoBot(config)

        import interfaces

        interfaces.__init__(bot, config)

        if starting_args.data_collector:
            Commands.data_collector(config)

        # start crypto bot options
        else:
            if starting_args.backtesting:
                import backtesting

                backtesting.__init__(bot)

                config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
                config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False

                config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
                config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

            if starting_args.simulate:
                config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
                config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

            if starting_args.risk is not None and 0 < starting_args.risk <= 1:
                config[CONFIG_TRADER][CONFIG_TRADER_RISK] = starting_args.risk

            if starting_args.start:
                Commands.start_bot(bot, logger)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OctoBot')
    parser.add_argument('start', help='start the OctoBot',
                        action='store_true')
    parser.add_argument('-s', '--simulate', help='start the OctoBot with the trader simulator',
                        action='store_true')
    parser.add_argument('-d', '--data_collector',
                        help='start the data collector process to create data for backtesting',
                        action='store_true')
    parser.add_argument('-u', '--update', help='update OctoBot with the latest version available',
                        action='store_true')
    parser.add_argument('-b', '--backtesting', help='enable the backtesting option and use the backtesting config',
                        action='store_true')
    parser.add_argument('-r', '--risk', type=float, help='risk representation (between 0 and 1)')
    parser.add_argument('-tp', '--pause_time', type=int, help='time to pause before starting the bot')
    parser.add_argument('-w', '--web', help='Start web server',
                        action='store_true')
    parser.add_argument('-t', '--telegram', help='Start telegram command handler',
                        action='store_true')
    parser.add_argument('-p', '--packager', help='Start OctoBot Tentacles Manager. examples: -p install all '
                                                 'to install all tentacles packages and -p install [tentacle] to '
                                                 'install specific tentacle. Tentacles Manager allows to install, '
                                                 'update, uninstall and reset tentacles. Use: -p help to get the '
                                                 'Tentacle Manager help.',
                        nargs='+')

    parser.add_argument('-c', '--creator', help='Start OctoBot Tentacles Creator. examples: -c Evaluator '
                                                'to create a new evaluator tentacles. Use: -c help to get the '
                                                'Tentacle Creator help.',
                        nargs='+')

    args = parser.parse_args()

    start_octobot(args)
