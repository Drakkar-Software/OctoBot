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

from tentacles_manager.tentacle_creator.tentacle_creator import TentacleCreator

from backtesting.collector.data_collector import DataCollector
from config import TENTACLES_DEFAULT_BRANCH, TENTACLES_FORCE_CONFIRM_PARAM
from config.config import encrypt
from interfaces import get_bot
from tools.logging.logging_util import get_logger
from tentacles_manager.tentacle_manager import TentacleManager


class Commands:

    @staticmethod
    def data_collector(config, catch=True):
        data_collector_inst = None
        try:
            data_collector_inst = DataCollector(config)
            asyncio.run(data_collector_inst.start())
        except Exception as e:
            data_collector_inst.stop()
            if catch:
                raise e

    @staticmethod
    def package_manager(config, commands, catch=False, force=False, default_git_branch=TENTACLES_DEFAULT_BRANCH):
        try:
            if TENTACLES_FORCE_CONFIRM_PARAM in commands:
                force = True
                commands.pop(commands.index(TENTACLES_FORCE_CONFIRM_PARAM))
            tentacle_manager = TentacleManager(config)
            tentacle_manager.parse_commands(commands, force=force, default_git_branch=default_git_branch)
        except Exception as e:
            if not catch:
                raise e

    @staticmethod
    def tentacle_creator(config, commands, catch=False):
        try:
            tentacle_creator_inst = TentacleCreator(config)
            tentacle_creator_inst.parse_commands(commands)
        except Exception as e:
            if not catch:
                raise e

    @staticmethod
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
                get_logger(Commands.__name__).error(f"Fail to encrypt your exchange keys, please try again ({e}).")
                raise e

    @staticmethod
    def start_strategy_optimizer(config, commands):
        from backtesting.strategy_optimizer.strategy_optimizer import StrategyOptimizer
        optimizer = StrategyOptimizer(config, commands[0])
        if optimizer.is_properly_initialized:
            optimizer.find_optimal_configuration()
            optimizer.print_report()

    @staticmethod
    def _signal_handler(_, __):
        # run Commands.BOT.stop_threads in thread because can't use the current asyncio loop
        stopping_thread = Thread(target=get_bot().stop)
        stopping_thread.start()
        stopping_thread.join()
        os._exit(0)

    @staticmethod
    async def start_bot(bot, logger, catch=False):
        try:
            loop = asyncio.get_event_loop()

            # handle CTRL+C signal
            signal.signal(signal.SIGINT, Commands._signal_handler)

            # start
            try:
                await bot.initialize()
                await bot.start()
            except CancelledError:
                logger.info("Core engine tasks cancelled.")

            # join threads in a not loop blocking executor
            # TODO remove this when no thread anymore
            await loop.run_in_executor(None, bot.task_manager.join_threads)

        except Exception as e:
            logger.exception(f"OctoBot Exception : {e}")
            if not catch:
                raise e
            Commands.stop_bot(bot)

    @staticmethod
    def stop_bot(bot):
        bot.stop()
        os._exit(0)

    @staticmethod
    def restart_bot():
        if sys.argv[0].endswith(".py"):
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            # prevent binary to add self as first argument
            os.execl(sys.executable, *sys.argv)
