import argparse
import logging
import sys
import traceback
from logging.config import fileConfig

from config.config import load_config
from config.cst import *
from cryptobot import CryptoBot
from interfaces.web.app import WebApp
from tools.commands import Commands


def _log_uncaught_exceptions(ex_cls, ex, tb):
    logging.exception(''.join(traceback.format_tb(tb)))
    logging.exception('{0}: {1}'.format(ex_cls, ex))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CryptoBot')
    parser.add_argument('start', help='start the CryptoBot',
                        action='store_true')
    parser.add_argument('--data_collector', help='start the data collector process to create data for backtesting',
                        action='store_true')
    parser.add_argument('--update', help='update CryptoBot with the latest version available',
                        action='store_true')
    parser.add_argument('--backtesting', help='enable the backtesting option and use the backtesting config',
                        action='store_true')
    parser.add_argument('--risk', type=float, default=0.5, help='risk representation (between 0 and 1)')
    parser.add_argument('--web', help='Start web server',
                        action='store_true')

    args = parser.parse_args()

    fileConfig('config/logging_config.ini')

    logger = logging.getLogger("MAIN")
    sys.excepthook = _log_uncaught_exceptions

    # Version
    logger.info("Version : {0}".format(LONG_VERSION))

    logger.info("Load config files...")
    config = load_config()
    config[CONFIG_EVALUATOR] = load_config(CONFIG_EVALUATOR_FILE, False)

    bot = CryptoBot(config)

    if args.web:
        import interfaces.web
        interfaces.web.__init__(bot)
        webapp = WebApp(config)
        webapp.start()

    if args.update:
        Commands.update(logger)

    elif args.data_collector:
        zipline_enabled = False
        if CONFIG_DATA_COLLECTOR_ZIPLINE in config[CONFIG_DATA_COLLECTOR]:
            zipline_enabled = config[CONFIG_DATA_COLLECTOR][CONFIG_DATA_COLLECTOR_ZIPLINE]

        if zipline_enabled:
            Commands.zipline_data_collector(config)
        else:
            Commands.data_collector(config)

    # start crypto bot options
    else:
        if args.backtesting:
            config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
            config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False

        if 0 < args.risk <= 1:
            config[CONFIG_TRADER][CONFIG_TRADER_RISK] = args.risk

        if args.start:
            Commands.start_bot(bot, logger)
