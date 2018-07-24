import time

from config.cst import *
from octobot import OctoBot
from tests.test_utils.config import load_test_config


def test_run_bot():
    # launch a bot
    config = load_test_config()
    bot = OctoBot(config)
    bot.time_frames = [TimeFrames.ONE_MINUTE]
    bot.create_exchange_traders()
    bot.create_evaluation_threads()
    bot.start_threads()

    # let it start
    time.sleep(5)

    # stop the bot
    bot.stop_threads()
