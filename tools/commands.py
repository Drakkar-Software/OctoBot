#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import os
import sys
import asyncio
import signal
from threading import Thread
from concurrent.futures import CancelledError

from octobot import get_bot, set_bot
from octobot_commons.config_util import encrypt

from tentacles_manager import TENTACLES_DEFAULT_BRANCH
from tentacles_manager.tentacle_creator.tentacle_creator import TentacleCreator

from octobot_commons.logging.logging_util import get_logger
from tentacles_manager.tentacle_manager import TentacleManager

COMMANDS_LOGGER_NAME = "Commands"


# TODO
def data_collector(config, catch=True):
    pass
#     data_collector_inst = None
#     try:
#         data_collector_inst = DataCollector(config)
#         asyncio.run(data_collector_inst.start())
#     except Exception as e:
#         data_collector_inst.stop()
#         if catch:
#             raise e


def package_manager(config, commands, catch=False, force=False, default_git_branch=TENTACLES_DEFAULT_BRANCH):
    try:
        # if TENTACLES_FORCE_CONFIRM_PARAM in commands: TODO
        #     force = True
        #     commands.pop(commands.index(TENTACLES_FORCE_CONFIRM_PARAM))
        # tentacle_manager = TentacleManager(config)
        # tentacle_manager.parse_commands(commands, force=force, default_git_branch=default_git_branch)
        pass
    except Exception as e:
        if not catch:
            raise e


def tentacle_creator(config, commands, catch=False):
    try:
        tentacle_creator_inst = TentacleCreator(config)
        tentacle_creator_inst.parse_commands(commands)
    except Exception as e:
        if not catch:
            raise e


def exchange_keys_encrypter(catch=False):
    try:
        api_key_crypted = encrypt(input("ENTER YOUR API-KEY : ")).decode()
        api_secret_crypted = encrypt(input("ENTER YOUR API-SECRET : ")).decode()
        print(f"Here are your encrypted exchanges keys : \n "
              f"\t- API-KEY : {api_key_crypted}\n"
              f"\t- API-SECRET : {api_secret_crypted}\n\n"
              f"Your new exchange key configuration is : \n"
              f'\t"api-key": "{api_key_crypted}",\n'
              f'\t"api-secret": "{api_secret_crypted}"\n')
    except Exception as e:
        if not catch:
            get_logger(COMMANDS_LOGGER_NAME).error(f"Fail to encrypt your exchange keys, please try again ({e}).")
            raise e


def start_strategy_optimizer(config, commands):
    from octobot_backtesting.api.strategy_optimizer import create_strategy_optimizer, \
        get_optimizer_is_properly_initialized, find_optimal_configuration, print_optimizer_report
    optimizer = create_strategy_optimizer(config, commands[0])
    if get_optimizer_is_properly_initialized(optimizer):
        find_optimal_configuration(optimizer)
        print_optimizer_report(optimizer)


def _signal_handler(_, __):
    # run Commands.BOT.stop_threads in thread because can't use the current asyncio loop
    stopping_thread = Thread(target=get_bot().task_manager.stop_tasks(), name="Commands signal_handler stop_tasks")
    stopping_thread.start()
    stopping_thread.join()
    os._exit(0)


async def start_bot(bot, logger, catch=False):
    try:
        loop = asyncio.get_event_loop()

        # handle CTRL+C signal
        signal.signal(signal.SIGINT, _signal_handler)

        # start
        try:
            set_bot(bot)
            await bot.initialize()
        except CancelledError:
            logger.info("Core engine tasks cancelled.")

        # join threads in a not loop blocking executor
        # TODO remove this when no thread anymore
        await bot.task_manager.join_tasks()

    except Exception as e:
        logger.exception(e, True, f"OctoBot Exception : {e}")
        if not catch:
            raise e
        stop_bot(bot)


def stop_bot(bot):
    bot.task_manager.stop_tasks()
    os._exit(0)


def restart_bot():
    if sys.argv[0].endswith(".py"):
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        # prevent binary to add self as first argument
        os.execl(sys.executable, *sys.argv)
