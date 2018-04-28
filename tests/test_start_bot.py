import time

from config.config import load_config
from config.cst import *
from cryptobot import CryptoBot


def test_create_bot():
    # launch a bot
    config = load_config()
    bot = CryptoBot(config)
    bot.create_exchange_traders()
    bot.stop_threads()


def test_run_bot():
    # launch a bot
    config = load_config()
    bot = CryptoBot(config)
    bot.time_frames = [TimeFrames.ONE_MINUTE]
    bot.create_exchange_traders()
    bot.create_evaluation_threads()
    bot.start_threads()

    # let it run 2 minutes: test will fail if an exception is raised
    # 1.9 to stop threads before the next time frame
    time.sleep(1.9*60)

    # stop the bot
    bot.stop_threads()
