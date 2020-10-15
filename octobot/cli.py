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
import argparse
import os
import sys

import octobot_commons.os_util as os_util
import octobot_commons.config as common_config
import octobot_commons.logging as logging
import octobot_commons.config_manager as config_manager
import octobot_commons.constants as common_constants
import octobot_commons.errors as errors

import octobot_services.api as service_api

import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.cli as tentacles_manager_cli

import octobot_trading.constants as trading_constants

import octobot.octobot as octobot_class
import octobot.commands as commands
import octobot.configuration_manager as configuration_manager
import octobot.octobot_backtesting_factory as octobot_backtesting
import octobot.constants as constants
import octobot.disclaimer as disclaimer
import octobot.logger as octobot_logger

try:
    import octobot_backtesting.constants as backtesting_constants
except ImportError as e:
    logging.get_logger().error("Can't start backtesting without the octobot_backtesting package properly installed.")
    raise e


def update_config_with_args(starting_args, config, logger):
    if starting_args.backtesting:
        if starting_args.backtesting_files:
            config[backtesting_constants.CONFIG_BACKTESTING][
                backtesting_constants.CONFIG_BACKTESTING_DATA_FILES] = starting_args.backtesting_files
        config[backtesting_constants.CONFIG_BACKTESTING][common_constants.CONFIG_ENABLED_OPTION] = True
        config[trading_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        config[trading_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True

    if starting_args.simulate:
        config[trading_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        config[trading_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True

    if starting_args.risk is not None and 0 < starting_args.risk <= 1:
        config[trading_constants.CONFIG_TRADING][trading_constants.CONFIG_TRADER_RISK] = starting_args.risk


# def _check_public_announcements(logger):
#     try:
#         announcement = get_external_resource(EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS)
#         if announcement:
#             logger.info(announcement)
#     except Exception as e:
#         logger.warning("Impossible to check announcements: {0}".format(e))


def _log_terms_if_unaccepted(config, logger):
    if not config_manager.accepted_terms(config):
        logger.info("*** Disclaimer ***")
        for line in disclaimer.DISCLAIMER:
            logger.info(line)
        logger.info("... Disclaimer ...")
    else:
        logger.info("Disclaimer accepted by user.")


def _disable_interface_from_param(interface_identifier, param_value, logger):
    if param_value:
        if service_api.disable_interfaces(interface_identifier) == 0:
            logger.warning("No " + interface_identifier + " interface to disable")
        else:
            logger.info(interface_identifier.capitalize() + " interface disabled")


def start_octobot(args):
    logger = None
    try:
        if args.version:
            print(constants.LONG_VERSION)
            return

        logger = octobot_logger.init_logger()

        # Version
        logger.info("Version : {0}".format(constants.LONG_VERSION))

        # Current running environment
        try:
            logger.debug(f"Running on {os_util.get_current_platform()} with {os_util.get_octobot_type()}")
        except Exception as e:
            logger.error(f"Impossible to identify the current running environment: {e}")

        # _check_public_announcements(logger)

        logger.info("Loading config files...")

        # configuration loading
        config = common_config.load_config(error=False, fill_missing_fields=True)

        if config is None and common_config.is_config_empty_or_missing():
            logger.info("No configuration found creating default...")
            configuration_manager.init_config()
            config = common_config.load_config(error=False)
        else:
            is_valid, e = config_manager.validate_config_file(config=config, schema_file=constants.CONFIG_FILE_SCHEMA)
            if not is_valid:
                logger.error("OctoBot can't repair your config.json file: invalid format: " + str(e))
                raise errors.ConfigError
            configuration_manager.config_health_check(config)

        if config is None:
            raise errors.ConfigError

        # Handle utility methods before bot initializing if possible
        if args.encrypter:
            commands.exchange_keys_encrypter()
            return

        # Add tentacles folder to Python path
        sys.path.append(os.path.realpath(os.getcwd()))

        if not tentacles_manager_api.load_tentacles(verbose=True):
            logger.info("OctoBot tentacles can't be found or are damaged. Installing default tentacles ...")
            commands.run_tentacles_installation()
            # reload tentacles
            tentacles_manager_api.load_tentacles(verbose=True)

        if args.strategy_optimizer:
            commands.start_strategy_optimizer(config, args.strategy_optimizer)
            return

        # In those cases load OctoBot
        _disable_interface_from_param("telegram", args.no_telegram, logger)
        _disable_interface_from_param("web", args.no_web, logger)

        update_config_with_args(args, config, logger)

        if args.backtesting:
            bot = octobot_backtesting.OctoBotBacktestingFactory(config,
                                                                run_on_common_part_only=not args.whole_data_range)
        else:
            bot = octobot_class.OctoBot(config, reset_trading_history=args.reset_trading_history)

        _log_terms_if_unaccepted(config, logger)

        commands.run_bot(bot, logger)

    except errors.ConfigError:
        logger.error("OctoBot can't start without " + common_constants.CONFIG_FILE
                     + " configuration file." + "\nYou can use " +
                     constants.DEFAULT_CONFIG_FILE + " as an example to fix it.")
        os._exit(-1)

    except ModuleNotFoundError as e:
        if 'tentacles' in str(e):
            logger.error("Impossible to start OctoBot, tentacles are missing.\nTo install tentacles, "
                         "please use the following command:\nstart.py tentacles --install --all")
        else:
            logger.exception(e)
        os._exit(-1)

    except errors.ConfigEvaluatorError:
        logger.error("OctoBot can't start without a valid  configuration file.\n"
                     "This file is generated on tentacle "
                     "installation using the following command:\nstart.py tentacles --install --all")
        os._exit(-1)

    except errors.ConfigTradingError:
        logger.error("OctoBot can't start without a valid configuration file.\n"
                     "This file is generated on tentacle "
                     "installation using the following command:\nstart.py tentacles --install --all")
        os._exit(-1)


def octobot_parser(parser):
    parser.add_argument('-v', '--version', help='Show OctoBot current version.',
                        action='store_true')
    parser.add_argument('-s', '--simulate', help='Force OctoBot to start with the trader simulator only.',
                        action='store_true')
    parser.add_argument('-rts', '--reset-trading-history', help='Force the traders to reset their history. They will '
                                                                'now take the next portfolio as a reference for '
                                                                'profitability and trading simulators will use a '
                                                                'fresh new portfolio.',
                        action='store_true')
    parser.add_argument('-b', '--backtesting', help='Start OctoBot in backesting mode using the backtesting '
                                                    'config stored in config.json.',
                        action='store_true')
    parser.add_argument('-bf', '--backtesting-files', type=str, nargs='+',
                        help='Backtesting files to use (should be provided with -b or --backtesting).',
                        required=False)
    parser.add_argument('-wdr', '--whole-data-range',
                        help='On multiple files backtesting: run on the whole available data instead of the '
                             'common part only (default behavior).',
                        action='store_true')
    parser.add_argument('-r', '--risk', type=float, help='Force a specific risk configuration (between 0 and 1).')
    parser.add_argument('-nw', '--no_web', help="Don't start OctoBot web interface.",
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
    parser.add_argument('-o', '--strategy_optimizer', help='Start Octobot strategy optimizer. This mode will make '
                                                           'octobot play backtesting scenarii located in '
                                                           'abstract_strategy_test.py with different timeframes, '
                                                           'evaluators and risk using the trading mode set in '
                                                           'config.json. This tool is useful to quickly test a '
                                                           'strategy and automatically find the best compatible '
                                                           'settings. Param is the name of the strategy class to '
                                                           'test. Example: -o TechnicalAnalysisStrategyEvaluator'
                                                           ' Warning: this process may take a long time.',
                        nargs='+')
    parser.set_defaults(func=start_octobot)

    # add sub commands
    subparsers = parser.add_subparsers(title="Other commands")

    # tentacles manager
    tentacles_parser = subparsers.add_parser("tentacles", help='Calls OctoBot tentacles manager.\n'
                                                               'Use "tentacles --help" to get the '
                                                               'tentacles manager help.')
    tentacles_manager_cli.register_tentacles_manager_arguments(tentacles_parser)
    tentacles_parser.set_defaults(func=commands.call_tentacles_manager)


def main(args=None):
    if not args:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(description='OctoBot')
    octobot_parser(parser)

    args = parser.parse_args(args)
    # call the appropriate command entry point
    args.func(args)
