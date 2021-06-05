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
import threading

import octobot_commons.configuration as configuration
import octobot_commons.logging as logging

import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.cli as tentacles_manager_cli

import octobot
import octobot.api.strategy_optimizer as strategy_optimizer_api
import octobot.logger as octobot_logger
import octobot.constants as constants
import octobot.configuration_manager as configuration_manager

COMMANDS_LOGGER_NAME = "Commands"
IGNORED_COMMAND_WHEN_RESTART = ["-u", "--update"]


def call_tentacles_manager(command_args):
    octobot_logger.init_logger()
    tentacles_urls = [
        configuration_manager.get_default_tentacles_url(),
        # tentacles_manager_api.get_compiled_tentacles_url(
        #     constants.DEFAULT_COMPILED_TENTACLES_URL,
        #     constants.TENTACLES_REQUIRED_VERSION
        # )
    ]
    sys.exit(tentacles_manager_cli.handle_tentacles_manager_command(command_args,
                                                                    tentacles_urls=tentacles_urls,
                                                                    bot_install_dir=os.getcwd()))
    

def exchange_keys_encrypter(catch=False):
    try:
        api_key_crypted = configuration.encrypt(input("ENTER YOUR API-KEY : ")).decode()
        api_secret_crypted = configuration.encrypt(input("ENTER YOUR API-SECRET : ")).decode()
        print(f"Here are your encrypted exchanges keys : \n "
              f"\t- API-KEY : {api_key_crypted}\n"
              f"\t- API-SECRET : {api_secret_crypted}\n\n"
              f"Your new exchange key configuration is : \n"
              f'\t"api-key": "{api_key_crypted}",\n'
              f'\t"api-secret": "{api_secret_crypted}"\n')
    except Exception as e:
        if not catch:
            logging.get_logger(COMMANDS_LOGGER_NAME).error(
                f"Fail to encrypt your exchange keys, please try again ({e}).")
            raise e


def start_strategy_optimizer(config, commands):
    tentacles_setup_config = tentacles_manager_api.get_tentacles_setup_config(config.get_tentacles_config_path())
    optimizer = strategy_optimizer_api.create_strategy_optimizer(config.config, tentacles_setup_config, commands[0])
    if strategy_optimizer_api.get_optimizer_is_properly_initialized(optimizer):
        strategy_optimizer_api.find_optimal_configuration(optimizer)
        strategy_optimizer_api.print_optimizer_report(optimizer)


def run_tentacles_install_or_update(config):
    asyncio.run(install_or_update_tentacles(config))


def run_update_or_repair_tentacles_if_necessary(config, tentacles_setup_config):
    asyncio.run(update_or_repair_tentacles_if_necessary(tentacles_setup_config, config))


async def update_or_repair_tentacles_if_necessary(tentacles_setup_config, config):
    if not tentacles_manager_api.are_tentacles_up_to_date(tentacles_setup_config, constants.VERSION):
        logging.get_logger(COMMANDS_LOGGER_NAME).info("OctoBot tentacles are not up to date. Updating tentacles...")
        if await install_or_update_tentacles(config):
            logging.get_logger(COMMANDS_LOGGER_NAME).info("OctoBot tentacles are now up to date.")
    elif tentacles_manager_api.load_tentacles(verbose=True):
        logging.get_logger(COMMANDS_LOGGER_NAME).debug("OctoBot tentacles are up to date.")
    else:
        logging.get_logger(COMMANDS_LOGGER_NAME).info("OctoBot tentacles are damaged. Installing default tentacles ...")
        await install_or_update_tentacles(config)


async def install_or_update_tentacles(config):
    await install_all_tentacles()
    # reload profiles
    config.load_profiles()
    # reload tentacles
    return tentacles_manager_api.load_tentacles(verbose=True)


async def install_all_tentacles(tentacles_url=None):
    if tentacles_url is None:
        tentacles_url = configuration_manager.get_default_tentacles_url()
    async with aiohttp.ClientSession() as aiohttp_session:
        await tentacles_manager_api.install_all_tentacles(tentacles_url,
                                                          aiohttp_session=aiohttp_session,
                                                          bot_install_dir=os.getcwd())
        # compiled_tentacles_url = tentacles_manager_api.get_compiled_tentacles_url(
        #     constants.DEFAULT_COMPILED_TENTACLES_URL,
        #     constants.TENTACLES_REQUIRED_VERSION
        # )
        # await tentacles_manager_api.install_all_tentacles(compiled_tentacles_url,
        #                                                   aiohttp_session=aiohttp_session,
        #                                                   bot_install_dir=constants.OCTOBOT_FOLDER)


def _signal_handler(_, __):
    # run Commands.BOT.stop_threads in thread because can't use the current asyncio loop
    stopping_thread = threading.Thread(target=octobot.get_bot().task_manager.stop_tasks(),
                                       name="Commands signal_handler stop_tasks")
    stopping_thread.start()
    stopping_thread.join()
    os._exit(0)


def run_bot(bot, logger):
    # handle CTRL+C signal
    try:
        signal.signal(signal.SIGINT, _signal_handler)
    except ValueError as e:
        logger.warning(f"Can't setup signal handler : {e}")

    # start bot
    bot.task_manager.run_forever(start_bot(bot, logger))


async def start_bot(bot, logger, catch=False):
    try:
        # load tentacles details
        tentacles_manager_api.reload_tentacle_info()
        # ensure tentacles config exists or create a new one
        await tentacles_manager_api.ensure_setup_configuration(bot_install_dir=os.getcwd())

        try:
            await bot.initialize()
        except asyncio.CancelledError:
            logger.info("Core engine tasks cancelled.")

    except Exception as e:
        logger.exception(e)
        if not catch:
            raise
        stop_bot(bot)


def stop_bot(bot, force=False):
    bot.task_manager.stop_tasks()
    if force:
        os._exit(0)


def get_bot_file():
    return sys.argv[0]


def restart_bot():
    argv = (f'{a}' for a in sys.argv if a not in IGNORED_COMMAND_WHEN_RESTART)
    if get_bot_file().endswith(".py"):
        os.execl(sys.executable, f'{sys.executable}', *argv)
    elif get_bot_file().endswith(constants.PROJECT_NAME):
        # restart from python OctoBot package entrypoint
        os.execl(get_bot_file(), *argv)
    else:
        # prevent binary to add self as first argument
        os.execl(sys.executable, *(f'"{a}"' for a in sys.argv))


def update_bot(bot_api):
    import octobot.updater.updater_factory as updater_factory
    bot_api.run_in_async_executor(updater_factory.create_updater().update())
