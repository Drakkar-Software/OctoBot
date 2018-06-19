import os
import subprocess

from backtesting.collector.data_collector import DataCollector
from config.cst import ORIGIN_URL
from tools.tentacle_manager.tentacle_manager import TentacleManager


class Commands:
    @staticmethod
    def update(logger, catch=False):
        logger.info("Updating...")
        try:
            process_set_remote = subprocess.Popen(["git", "remote", "set-url", "origin", ORIGIN_URL],
                                                  stdout=subprocess.PIPE)
            _ = process_set_remote.communicate()[0]

            process_pull = subprocess.Popen(["git", "pull", "origin"], stdout=subprocess.PIPE)
            _ = process_pull.communicate()[0]

            process_checkout = subprocess.Popen(["git", "checkout", "beta"], stdout=subprocess.PIPE)
            _ = process_checkout.communicate()[0]

            logger.info("Updated")
        except Exception as e:
            logger.info("Exception raised during updating process...")
            if not catch:
                raise e

    @staticmethod
    def data_collector(config, catch=False):
        data_collector_inst = None
        try:
            data_collector_inst = DataCollector(config)
            data_collector_inst.join()
        except Exception as e:
            data_collector_inst.stop()
            if not catch:
                raise e

    @staticmethod
    def package_manager(config, commands, catch=False):
        try:
            package_manager_inst = TentacleManager(config)
            package_manager_inst.parse_commands(commands)
        except Exception as e:
            if not catch:
                raise e

    @staticmethod
    def start_bot(bot, logger, catch=False):
        bot.create_exchange_traders()
        bot.create_evaluation_threads()
        try:
            bot.start_threads()
            bot.join_threads()
        except Exception as e:
            logger.exception("CryptBot Exception : {0}".format(e))
            if not catch:
                raise e
            Commands.stop_bot(bot)

    @staticmethod
    def stop_bot(bot):
        bot.stop_threads()
        os._exit(0)

