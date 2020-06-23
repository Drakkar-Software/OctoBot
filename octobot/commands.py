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

import aiohttp
import sys
import asyncio
import signal
from threading import Thread
from concurrent.futures import CancelledError

from octobot_tentacles_manager.api.installer import install_all_tentacles

from octobot.constants import DEFAULT_TENTACLES_URL, OCTOBOT_FOLDER
from octobot import get_bot, set_bot
from octobot_commons.config_util import encrypt
from octobot_tentacles_manager.api.configurator import get_tentacles_setup_config, ensure_setup_configuration
from octobot_commons.logging.logging_util import get_logger
from octobot_tentacles_manager.api.loader import reload_tentacle_info
from octobot_tentacles_manager.cli import handle_tentacles_manager_command
from octobot.logger import init_logger

COMMANDS_LOGGER_NAME = "Commands"


def call_tentacles_manager(command_args):
    init_logger()
    sys.exit(handle_tentacles_manager_command(command_args,
                                              tentacles_url=DEFAULT_TENTACLES_URL,
                                              bot_install_dir=OCTOBOT_FOLDER))


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
    from octobot.api.strategy_optimizer import create_strategy_optimizer, \
        get_optimizer_is_properly_initialized, find_optimal_configuration, print_optimizer_report
    tentacles_setup_config = get_tentacles_setup_config()
    optimizer = create_strategy_optimizer(config, tentacles_setup_config, commands[0])
    if get_optimizer_is_properly_initialized(optimizer):
        find_optimal_configuration(optimizer)
        print_optimizer_report(optimizer)


def run_tentacles_installation():
    asyncio.run(_install_all_tentacles())


async def _install_all_tentacles():
    async with aiohttp.ClientSession() as aiohttp_session:
        await install_all_tentacles(DEFAULT_TENTACLES_URL,
                                    aiohttp_session=aiohttp_session,
                                    bot_install_dir=OCTOBOT_FOLDER)


def _signal_handler(_, __):
    # run Commands.BOT.stop_threads in thread because can't use the current asyncio loop
    stopping_thread = Thread(target=get_bot().task_manager.stop_tasks(), name="Commands signal_handler stop_tasks")
    stopping_thread.start()
    stopping_thread.join()
    os._exit(0)


def run_bot(bot, logger):
    # handle CTRL+C signal
    signal.signal(signal.SIGINT, _signal_handler)

    # start bot
    bot.task_manager.run_forever(start_bot(bot, logger))


async def start_bot(bot, logger, catch=False):
    try:
        # load tentacles details
        reload_tentacle_info()
        # ensure tentacles config exists or create a new one
        await ensure_setup_configuration(bot_install_dir=OCTOBOT_FOLDER)

        # start
        try:
            set_bot(bot)
            await bot.initialize()
        except CancelledError:
            logger.info("Core engine tasks cancelled.")

    except Exception as e:
        logger.exception(e, True, f"OctoBot Exception : {e}")
        if not catch:
            raise e
        stop_bot(bot)


def stop_bot(bot, force=False):
    bot.task_manager.stop_tasks()
    if force:
        os._exit(0)


def restart_bot():
    if sys.argv[0].endswith(".py"):
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        # prevent binary to add self as first argument
        os.execl(sys.executable, *sys.argv)
