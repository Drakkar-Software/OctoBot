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

from tools.logging.logging_util import get_logger
import os
import sys
import asyncio

from backtesting.collector.data_collector import DataCollector
from config.config import encrypt
from tools.tentacle_creator.tentacle_creator import TentacleCreator
from tools.tentacle_manager.tentacle_manager import TentacleManager


class Commands:
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
    def package_manager(config, commands, catch=False, force=False):
        try:
            package_manager_inst = TentacleManager(config)
            package_manager_inst.parse_commands(commands, force=force)
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
    async def start_bot(bot, logger, catch=False):
        try:
            loop = asyncio.get_event_loop()
            # try to init
            await bot.create_exchange_traders()
            bot.create_evaluation_threads()

            # try to start
            await bot.start_tasks()

            # join threads in a not loop blocking executor
            #TODO remove this when no thread anymore
            await loop.run_in_executor(None, bot.join_threads)

        except Exception as e:
            logger.exception(f"OctoBot Exception : {e}")
            if not catch:
                raise e
            Commands.stop_bot(bot)

    @staticmethod
    def stop_bot(bot):
        bot.stop_threads()
        os._exit(0)

    @staticmethod
    def restart_bot():
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)
