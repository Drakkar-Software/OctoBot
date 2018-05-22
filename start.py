import argparse
import logging
import sys
import traceback
from logging.config import fileConfig

from config.config import load_config
from config.cst import *
from cryptobot import CryptoBot
from interfaces.telegram.bot import TelegramApp
from services import WebService
from tools.commands import Commands


def _log_uncaught_exceptions(ex_cls, ex, tb):
    logging.exception(''.join(traceback.format_tb(tb)))
    logging.exception('{0}: {1}'.format(ex_cls, ex))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CryptoBot')
    parser.add_argument('start', help='start the CryptoBot',
                        action='store_true')
    parser.add_argument('-s', '--simulate', help='start the CryptoBot with the trader simulator',
                        action='store_true')
    parser.add_argument('-d', '--data_collector', help='start the data collector process to create data for backtesting',
                        action='store_true')
    parser.add_argument('-u', '--update', help='update CryptoBot with the latest version available',
                        action='store_true')
    parser.add_argument('-b', '--backtesting', help='enable the backtesting option and use the backtesting config',
                        action='store_true')
    parser.add_argument('-r', '--risk', type=float, help='risk representation (between 0 and 1)')
    parser.add_argument('-w', '--web', help='Start web server',
                        action='store_true')
    parser.add_argument('-t', '--telegram', help='Start telegram command handler',
                        action='store_true')
    parser.add_argument('-p', '--packager', help='Start CryptoBot package manager', nargs='+')

    args = parser.parse_args()

    fileConfig('config/logging_config.ini')

    logger = logging.getLogger("CryptoBot Launcher")

    # Force new log file creation not to log at the previous one's end.
    logger.parent.handlers[1].doRollover()

    sys.excepthook = _log_uncaught_exceptions

    # Version
    logger.info("Version : {0}".format(LONG_VERSION))

    logger.info("Loading config files...")
    config = load_config()
    config[CONFIG_EVALUATOR] = load_config(CONFIG_EVALUATOR_FILE, False)

    TelegramApp.enable(config, args.telegram)

    WebService.enable(config, args.web)

    bot = CryptoBot(config)

    import interfaces
    interfaces.__init__(bot, config)

    if args.update:
        Commands.update(logger)

    elif args.data_collector:
        Commands.data_collector(config)

    elif args.packager:
        Commands.package_manager(config, args.packager)

    # start crypto bot options
    else:
        if args.backtesting:
            import backtesting
            backtesting.__init__(bot)

            config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
            config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False

            config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
            config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

        if args.simulate:
            config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
            config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

        if args.risk is not None and 0 < args.risk <= 1:
            config[CONFIG_TRADER][CONFIG_TRADER_RISK] = args.risk

        if args.start:
            Commands.start_bot(bot, logger)
