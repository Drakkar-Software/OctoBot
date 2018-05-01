import logging
import subprocess
import sys
import traceback
from logging.config import fileConfig

from backtesting.collector.data_collector import DataCollector
from backtesting.collector.zipline_data_collector import ZiplineDataCollector
from cryptobot import CryptoBot
import argparse

from config.config import load_config
from config.cst import *


def _log_uncaught_exceptions(ex_cls, ex, tb):
    logging.exception(''.join(traceback.format_tb(tb)))
    logging.exception('{0}: {1}'.format(ex_cls, ex))


def start_crypto_bot(config):
    bot = CryptoBot(config)
    bot.create_exchange_traders()
    bot.create_evaluation_threads()
    try:
        bot.start_threads()
        bot.join_threads()
    except Exception as e:
        logging.exception("CryptBot Exception : {0}".format(e))
        bot.stop_threads()
        raise e


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CryptoBot')
    parser.add_argument('start', help='start the CryptoBot',
                        action='store_true')
    parser.add_argument('--data_collector', help='start the data collector process to create data for backtesting',
                        action='store_true')
    parser.add_argument('--update', help='update the cryptobot with the last version available',
                        action='store_true')
    parser.add_argument('--backtesting', help='enable the backtesting option and use the backtesting config',
                        action='store_true')
    parser.add_argument('--risk', type=float, default=0.5, help='Risk representation (between 0 and 1)')

    args = parser.parse_args()

    fileConfig('config/logging_config.ini')

    logger = logging.getLogger("MAIN")
    sys.excepthook = _log_uncaught_exceptions

    # Version
    logger.info("Version : {0}".format(LONG_VERSION))

    logger.info("Load config files...")
    config = load_config()
    config[CONFIG_EVALUATOR] = load_config(CONFIG_EVALUATOR_FILE, False)

    if args.update:
        logger.info("Updating...")
        try:
            process_set_remote = subprocess.Popen(["git", "remote", "set-url", "origin", ORIGIN_URL], stdout=subprocess.PIPE)
            output = process_set_remote.communicate()[0]

            process_pull = subprocess.Popen(["git", "pull", "origin"], stdout=subprocess.PIPE)
            output = process_pull.communicate()[0]

            logger.info("Updated")
        except Exception as e:
            logger.info("Exception raised during updating process...")
            raise e

    elif args.data_collector:
        zipline_enabled = False
        if CONFIG_DATA_COLLECTOR_ZIPLINE in config[CONFIG_DATA_COLLECTOR]:
            zipline_enabled = config[CONFIG_DATA_COLLECTOR][CONFIG_DATA_COLLECTOR_ZIPLINE]

        if zipline_enabled:
            data_collector_inst = ZiplineDataCollector(config)
        else:
            data_collector_inst = DataCollector(config)

        # data_collector_inst.stop()
        data_collector_inst.join()

    # start crypto bot options
    else:
        if args.backtesting:
            config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
            config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False

        if 0 < args.risk <= 1:
            config[CONFIG_TRADER][CONFIG_TRADER_RISK] = args.risk

        if args.start:
            start_crypto_bot(config)
