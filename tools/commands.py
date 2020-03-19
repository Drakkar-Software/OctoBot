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
import aiohttp
from threading import Thread
from concurrent.futures import CancelledError

from config import FORCE_ARG, ALL_ARG, UNINSTALL_ARG, UPDATE_ARG, INSTALL_ARG, HELP_ARG, DEFAULT_TENTACLES_URL
from octobot import get_bot, set_bot
from octobot_commons.config_util import encrypt
from octobot_tentacles_manager.api.creator import start_tentacle_creator
from octobot_commons.logging.logging_util import get_logger
from octobot_tentacles_manager.api.installer import install_all_tentacles, install_tentacles, \
    USER_HELP as INSTALL_USER_HELP
from octobot_tentacles_manager.api.loader import reload_tentacle_info
from octobot_tentacles_manager.api.uninstaller import uninstall_all_tentacles, uninstall_tentacles, \
    USER_HELP as UNINSTALL_USER_HELP
from octobot_tentacles_manager.api.updater import update_all_tentacles, update_tentacles, \
    USER_HELP as UPDATE_USER_HELP

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


def _check_arg_and_cleanup(command_args, argument):
    if argument in command_args:
        command_args.pop(command_args.index(argument))
        return True
    return False


async def _handle_package_manager_command(command_args, aiohttp_session=None):
    aiohttp_session = aiohttp_session or aiohttp.ClientSession()
    force = _check_arg_and_cleanup(command_args, FORCE_ARG)
    all = _check_arg_and_cleanup(command_args, ALL_ARG)
    install = _check_arg_and_cleanup(command_args, INSTALL_ARG)
    update = _check_arg_and_cleanup(command_args, UPDATE_ARG)
    uninstall = _check_arg_and_cleanup(command_args, UNINSTALL_ARG)

    if not (all or command_args):
        get_logger(COMMANDS_LOGGER_NAME).error("Please provide at least one tentacle name or add the 'all' parameter")
    elif install:
        if all:
            await install_all_tentacles(DEFAULT_TENTACLES_URL, aiohttp_session=aiohttp_session)
        else:
            await install_tentacles(command_args, DEFAULT_TENTACLES_URL, aiohttp_session=aiohttp_session)
    elif update:
        if all:
            await update_all_tentacles(DEFAULT_TENTACLES_URL, aiohttp_session=aiohttp_session)
        else:
            await update_tentacles(command_args, DEFAULT_TENTACLES_URL, aiohttp_session=aiohttp_session)
    elif uninstall:
        if all:
            await uninstall_all_tentacles(DEFAULT_TENTACLES_URL, use_confirm_prompt=force)
        else:
            await uninstall_tentacles(command_args, DEFAULT_TENTACLES_URL, use_confirm_prompt=force)


def _print_tentacle_manager_help():
    help_message = f"""Welcome to OctoBot tentacles package manager.
Available commands are:
    - {INSTALL_ARG}: {INSTALL_USER_HELP}
    - {UPDATE_ARG}: {UPDATE_USER_HELP}
    - {UNINSTALL_ARG}: {UNINSTALL_USER_HELP}

Protip: For each command, you can use the 'all' parameter to apply the command to all tentacles or apply the command to one 
or many tentacles by naming them."""
    print(help_message)


def package_manager(command_args, catch=False, aiohttp_session=None):
    try:
        if _check_arg_and_cleanup(command_args, HELP_ARG):
            _print_tentacle_manager_help()
        else:
            asyncio.run(_handle_package_manager_command(command_args, aiohttp_session))
    except Exception as e:
        if not catch:
            raise e


def tentacle_creator(config, commands, catch=False):
    try:
        start_tentacle_creator(config, commands)
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
        # handle CTRL+C signal
        signal.signal(signal.SIGINT, _signal_handler)

        # load tentacles details
        await reload_tentacle_info()

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
