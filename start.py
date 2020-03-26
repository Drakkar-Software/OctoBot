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

from octobot_commons.errors import ConfigError, ConfigTradingError
from octobot_evaluators.util.errors import ConfigEvaluatorError
from octobot_interfaces.api.interfaces import disable_interfaces

from tools.commands import package_manager, tentacle_creator, exchange_keys_encrypter, start_strategy_optimizer, \
    start_bot, data_collector
from tools.config_manager import config_health_check
from octobot_commons.config import load_config, is_config_empty_or_missing, init_config

from config import LONG_VERSION, FORCE_ASYNCIO_DEBUG_OPTION, LOGGING_CONFIG_FILE, INSTALL_ARG, ALL_ARG, UPDATE_ARG, \
    UNINSTALL_ARG, FORCE_ARG, HELP_ARG
from octobot_commons.constants import CONFIG_ENABLED_OPTION, CONFIG_FILE, DEFAULT_CONFIG_FILE
from octobot_trading.constants import CONFIG_TRADER, CONFIG_SIMULATOR, CONFIG_TRADING, CONFIG_TRADER_RISK
from octobot_commons.config_manager import validate_config_file, accepted_terms, is_in_dev_mode

import argparse
import asyncio
import logging
import os
import sys
import traceback
import webbrowser
import socket
from logging.config import fileConfig
from time import sleep

from config.disclaimer import DISCLAIMER
from octobot_tentacles_manager.api.loader import load_tentacles


# Keep string '+' operator to ensure backward compatibility in this file


def _log_uncaught_exceptions(ex_cls, ex, tb):
    logging.exception(''.join(traceback.format_tb(tb)))
    logging.exception('{0}: {1}'.format(ex_cls, ex))


def update_config_with_args(starting_args, config, logger):
    if starting_args.backtesting:
        try:
            from octobot_backtesting.constants import CONFIG_BACKTESTING, CONFIG_ANALYSIS_ENABLED_OPTION
            config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
            config[CONFIG_BACKTESTING][CONFIG_ANALYSIS_ENABLED_OPTION] = starting_args.backtesting_analysis
        except ImportError as e:
            logger.error("Can't start backtesting without the octobot_backtesting package properly installed.")
            raise e
        # config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION] = False

        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
        config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

    if starting_args.simulate:
        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
        config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

    if starting_args.risk is not None and 0 < starting_args.risk <= 1:
        config[CONFIG_TRADING][CONFIG_TRADER_RISK] = starting_args.risk


# def _check_public_announcements(logger):
#     try:
#         announcement = get_external_resource(EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS)
#         if announcement:
#             logger.info(announcement)
#     except Exception as e:
#         logger.warning("Impossible to check announcements: {0}".format(e))


# def _auto_open_web(config, bot):
#     try:
#         # wait bot is ready
#         while not bot.is_ready():
#             sleep(0.1)
#
#         webbrowser.open("http://{0}:{1}".format(socket.gethostbyname(socket.gethostname()),
#                                                 config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT])
#                         )
#     except webbrowser.Error as e:
#         logging.error("{0}, impossible to open automatically web interface".format(e))


def _log_terms_if_unaccepted(config, logger):
    if not accepted_terms(config):
        logger.info("*** Disclaimer ***")
        for line in DISCLAIMER:
            logger.info(line)
        logger.info("... Disclaimer ...")
    else:
        logger.info("Disclaimer accepted by user.")


def _disable_interface_from_param(interface_identifier, param_value, logger):
    if param_value:
        if disable_interfaces(interface_identifier) == 0:
            logger.warning(f"No {interface_identifier} interface to disable")
        else:
            logger.info(f"{interface_identifier.capitalize()} interface disabled")


def _init_logger():
    try:
        fileConfig(LOGGING_CONFIG_FILE)
    except KeyError:
        print("Impossible to start OctoBot: the logging configuration can't be found in '" + LOGGING_CONFIG_FILE +
              "' please make sure you are running OctoBot from its root directory.")
        os._exit(-1)

    logger = logging.getLogger("OctoBot Launcher")

    try:
        # Force new log file creation not to log at the previous one's end.
        logger.parent.handlers[1].doRollover()
    except PermissionError:
        print("Impossible to start OctoBot: the logging file is locked, this is probably due to another running "
              "OctoBot instance.")
        os._exit(-1)

    sys.excepthook = _log_uncaught_exceptions
    return logger


def start_octobot(starting_args):
    try:
        if starting_args.version:
            print(LONG_VERSION)
        else:
            logger = _init_logger()

            # Version
            logger.info("Version : {0}".format(LONG_VERSION))

            # _check_public_announcements(logger)

            logger.info("Loading config files...")

            # configuration loading
            config = load_config(error=False, fill_missing_fields=True)

            if config is None and is_config_empty_or_missing():
                logger.info("No configuration found creating default...")
                init_config()
                config = load_config(error=False)
            else:
                is_valid, e = validate_config_file(config=config)
                if not is_valid:
                    logger.error("OctoBot can't repair your config.json file: invalid format: " + str(e))
                    raise ConfigError
                config_health_check(config)

            if config is None:
                raise ConfigError

            # Handle utility methods before bot initializing if possible
            if starting_args.packager:
                package_manager(starting_args.packager)

            elif starting_args.creator:
                tentacle_creator(config, starting_args.creator)

            elif starting_args.encrypter:
                exchange_keys_encrypter()

            else:
                if not load_tentacles(verbose=True):
                    logger.info("No tentacles found. Installing default tentacles ...")
                    package_manager([INSTALL_ARG, ALL_ARG])
                    # reload tentacles
                    load_tentacles(verbose=True)

                if starting_args.data_collector:
                    data_collector(config)

                elif starting_args.strategy_optimizer:
                    start_strategy_optimizer(config, starting_args.strategy_optimizer)

                else:

                    # In those cases load OctoBot
                    from octobot.octobot import OctoBot

                    _disable_interface_from_param("telegram", starting_args.no_telegram, logger)
                    _disable_interface_from_param("web", starting_args.no_web, logger)

                    update_config_with_args(starting_args, config, logger)

                    reset_trading_history = starting_args.reset_trading_history

                    bot = OctoBot(config, reset_trading_history=reset_trading_history)

                    _log_terms_if_unaccepted(config, logger)

                    # import interfaces
                    # interfaces.__init__(bot, config)

                    # if not starting_args.no_open_web and not starting_args.no_web:
                    #     Thread(target=_auto_open_web, args=(config, bot)).start()

                    # set debug_mode = True to activate asyncio debug mode
                    debug_mode = is_in_dev_mode(config) or FORCE_ASYNCIO_DEBUG_OPTION
                    asyncio.run(start_bot(bot, logger), debug=debug_mode)
    except ConfigError:
        logger.error("OctoBot can't start without " + CONFIG_FILE + " configuration file." + "\nYou can use " +
                     DEFAULT_CONFIG_FILE + " as an example to fix it.")
        os._exit(-1)

    except ModuleNotFoundError as e:
        if 'tentacles' in str(e):
            logger.error("Impossible to start OctoBot, tentacles are missing.\nTo install tentacles, "
                         "please use the following command:\nstart.py -p install all")
        else:
            logger.exception(e)
        os._exit(-1)

    except ConfigEvaluatorError:
        logger.error("OctoBot can't start without a valid  configuration file.\n"
                     "This file is generated on tentacle "
                     "installation using the following command:\nstart.py -p install all")
        os._exit(-1)

    except ConfigTradingError:
        logger.error("OctoBot can't start without a valid configuration file.\n"
                     "This file is generated on tentacle "
                     "installation using the following command:\nstart.py -p install all")
        os._exit(-1)


def main(args=None):
    if not args:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description='OctoBot')
    parser.add_argument('-v', '--version', help='Show OctoBot current version.',
                        action='store_true')
    parser.add_argument('-s', '--simulate', help='Force OctoBot to start with the trader simulator only.',
                        action='store_true')
    parser.add_argument('-rts', '--reset-trading-history', help='Force the traders to reset their history. They will '
                                                                'now take the next portfolio as a reference for '
                                                                'profitability and trading simulators will use a '
                                                                'fresh new portfolio.',
                        action='store_true')
    parser.add_argument('-d', '--data_collector',
                        help='Start the data collector process to store data for backtesting.',
                        action='store_true')
    parser.add_argument('-b', '--backtesting', help='Start OctoBot in backesting mode using the backtesting '
                                                    'config stored in config.json.',
                        action='store_true')
    parser.add_argument('-ba', '--backtesting_analysis',
                        help='Additional argument in order not stop the bot at the end of the backtesting '
                             '(useful to analyse results using interfaces like the web interface).',
                        action='store_true')
    parser.add_argument('-r', '--risk', type=float, help='Force a specific risk configuration (between 0 and 1).')
    parser.add_argument('-nw', '--no_web', help="Don't start OctoBot web interface.",
                        action='store_true')
    parser.add_argument('-no', '--no_open_web', help="Don't automatically open web interface.",
                        action='store_true')
    parser.add_argument('-nt', '--no-telegram', help='Start OctoBot without telegram interface, even if telegram '
                                                     'credentials are in config. With this parameter, your Octobot '
                                                     'won`t reply to any telegram command but is still able to listen '
                                                     'to telegram feed and send telegram notifications',
                        action='store_true')
    parser.add_argument('--encrypter', help="Start the exchange api keys encrypter. This tool is useful to manually add"
                                            " exchanges configuration in your config.json without using any interface "
                                            "(ie the web interface that handle encryption automatically)",
                        action='store_true')
    parser.add_argument('-p', '--packager', help='Start OctoBot Tentacles Manager. examples: -p' + INSTALL_ARG +
                                                 ALL_ARG + ' to install all tentacles packages and -p ' + INSTALL_ARG +
                                                 ' [tentacle] to install specific tentacle. Tentacles Manager allows '
                                                 'to ' + INSTALL_ARG + ', ' + UPDATE_ARG + ' and ' + UNINSTALL_ARG +
                                                 ' tentacles.' 'You can also skip uninstalling confirm inputs '
                                                 'by adding the ' + FORCE_ARG + ' option. '
                                                 'Use: -p ' + HELP_ARG + ' to get the Tentacle Manager help.',
                        nargs='+')

    parser.add_argument('-c', '--creator', help='Start OctoBot Tentacles Creator. examples: -c Evaluator '
                                                'to create a new evaluator tentacles. Use: -c help to get the '
                                                'Tentacle Creator help.',
                        nargs='+')

    parser.add_argument('-o', '--strategy_optimizer', help='Start Octobot strategy optimizer. This mode will make '
                                                           'octobot play backtesting scenarii located in '
                                                           'abstract_strategy_test.py with different timeframes, '
                                                           'evaluators and risk using the trading mode set in '
                                                           'config.json. This tool is useful to quickly test a '
                                                           'strategy and automatically find the best compatible '
                                                           'settings. Param is the name of the strategy class to '
                                                           'test. Example: -o FullMixedStrategiesEvaluator'
                                                           ' Warning: this process may take a long time.',
                        nargs='+')

    args = parser.parse_args(args)

    start_octobot(args)


if __name__ == '__main__':
    main()
