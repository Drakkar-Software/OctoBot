import logging
from logging.config import fileConfig

from backtesting.collector.data_collector import DataCollector
from bot import CryptoBot
import argparse

from config.config import load_config
from config.cst import VERSION

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CryptoBot')
    parser.add_argument('start', help='start the CryptoBot',
                        action='store_true')
    parser.add_argument('--data_collector', help='start the data collector process to create data for backtesting',
                        action='store_true')

    args = parser.parse_args()

    fileConfig('config/logging_config.ini')

    logger = logging.getLogger("MAIN")

    # Version
    logger.info("Version : {0}".format(VERSION))

    logger.info("Load config files...")
    config = load_config()

    if args.data_collector:
        data_collector_inst = DataCollector(config)
        # data_collector_inst.stop()
        data_collector_inst.join()

    elif args.start:
        bot = CryptoBot(config)
        bot.create_exchange_traders()
        bot.create_evaluation_threads()
        bot.start_threads()
        bot.join_threads()
