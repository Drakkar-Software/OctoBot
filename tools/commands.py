import subprocess

from backtesting.collector.data_collector import DataCollector
from backtesting.collector.zipline_data_collector import ZiplineDataCollector
from cryptobot import CryptoBot


class Commands:
    @staticmethod
    def update(logger, catch=False):
        logger.info("Updating...")
        try:
            process_set_remote = subprocess.Popen(["git", "remote", "set-url", "origin", ORIGIN_URL],
                                                  stdout=subprocess.PIPE)
            output = process_set_remote.communicate()[0]

            process_pull = subprocess.Popen(["git", "pull", "origin"], stdout=subprocess.PIPE)
            output = process_pull.communicate()[0]

            logger.info("Updated")
        except Exception as e:
            logger.info("Exception raised during updating process...")
            if not catch:
                raise e

    @staticmethod
    def zipline_data_collector(config, catch=False):
        data_collector_inst = None
        try:
            data_collector_inst = ZiplineDataCollector(config)
            data_collector_inst.join()
        except Exception as e:
            data_collector_inst.stop()
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
    def start_bot(config, logger, catch=False):
        bot = CryptoBot(config)
        bot.create_exchange_traders()
        bot.create_evaluation_threads()
        try:
            bot.start_threads()
            bot.join_threads()
        except Exception as e:
            logger.exception("CryptBot Exception : {0}".format(e))
            bot.stop_threads()
            if not catch:
                raise e
