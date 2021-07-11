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
# prevents distutils_patch.py:26: UserWarning: Distutils was imported before Setuptools. This usage is discouraged
# and may exhibit undesirable behaviors or errors. Please use Setuptools' objects directly or at least import Setuptools
# first
import setuptools
from distutils.version import LooseVersion

import argparse
import os
import sys
import multiprocessing

import octobot_commons.os_util as os_util
import octobot_commons.logging as logging
import octobot_commons.configuration as configuration
import octobot_commons.constants as common_constants
import octobot_commons.errors as errors

import octobot_services.api as service_api

import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.cli as tentacles_manager_cli
import octobot_tentacles_manager.constants as tentacles_manager_constants

import octobot
import octobot.octobot as octobot_class
import octobot.commands as commands
import octobot.configuration_manager as configuration_manager
import octobot.octobot_backtesting_factory as octobot_backtesting
import octobot.constants as constants
import octobot.disclaimer as disclaimer
import octobot.logger as octobot_logger


def update_config_with_args(starting_args, config: configuration.Configuration, logger):
    try:
        import octobot_backtesting.constants as backtesting_constants
    except ImportError as e:
        logging.get_logger().error(
            "Can't start backtesting without the octobot_backtesting package properly installed.")
        raise e

    if starting_args.backtesting:
        if starting_args.backtesting_files:
            config.config[backtesting_constants.CONFIG_BACKTESTING][
                backtesting_constants.CONFIG_BACKTESTING_DATA_FILES] = starting_args.backtesting_files
        config.config[backtesting_constants.CONFIG_BACKTESTING][common_constants.CONFIG_ENABLED_OPTION] = True
        config.config[common_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        config.config[common_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True

    if starting_args.simulate:
        config.config[common_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        config.config[common_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True

    if starting_args.risk is not None and 0 < starting_args.risk <= 1:
        config.config[common_constants.CONFIG_TRADING][common_constants.CONFIG_TRADER_RISK] = starting_args.risk


# def _check_public_announcements(logger):
#     try:
#         announcement = get_external_resource(EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS)
#         if announcement:
#             logger.info(announcement)
#     except Exception as e:
#         logger.warning("Impossible to check announcements: {0}".format(e))


def _log_terms_if_unaccepted(config: configuration.Configuration, logger):
    if not config.accepted_terms():
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


def _log_environment(logger):
    try:
        logger.debug(f"Running on {os_util.get_current_platform()} with {os_util.get_octobot_type()}")
    except Exception as e:
        logger.error(f"Impossible to identify the current running environment: {e}")


def _create_configuration():
    config_path = configuration.get_user_config()
    config = configuration.Configuration(config_path,
                                         common_constants.USER_PROFILES_FOLDER,
                                         constants.CONFIG_FILE_SCHEMA,
                                         constants.PROFILE_FILE_SCHEMA)
    return config


def _create_startup_config(logger):
    logger.info("Loading config files...")
    config = _create_configuration()
    if config.is_config_file_empty_or_missing():
        logger.info("No configuration found creating default configuration...")
        configuration_manager.init_config()
        config.read(should_raise=False)
    else:
        _read_config(config, logger)
        _validate_config(config, logger)
    return config


def _read_config(config, logger):
    try:
        config.read(should_raise=False, fill_missing_fields=True)
    except errors.NoProfileError:
        _repair_with_default_profile(config, logger)
        config = _create_configuration()
        config.read(should_raise=False, fill_missing_fields=True)


def _validate_config(config, logger):
    try:
        config.validate()
    except Exception as err:
        if configuration_manager.migrate_from_previous_config(config):
            logger.info("Your configuration has been migrated into the newest format.")
        else:
            logger.error("OctoBot can't repair your config.json file: invalid format: " + str(err))
            raise errors.ConfigError from err


def _repair_with_default_profile(config, logger):
    logger.error("OctoBot can't start without a valid profile configuration. Selecting default profile ...")
    configuration_manager.set_default_profile(config)
    config.load_profiles_if_possible_and_necessary()


def _load_or_create_tentacles(config, logger):
    # add tentacles folder to Python path
    sys.path.append(os.path.realpath(os.getcwd()))

    # when tentacles folder already exists
    if os.path.isfile(tentacles_manager_constants.USER_REFERENCE_TENTACLE_CONFIG_FILE_PATH):
        config.load_profiles_if_possible_and_necessary()
        tentacles_setup_config = tentacles_manager_api.get_tentacles_setup_config(
            config.get_tentacles_config_path())
        commands.run_update_or_repair_tentacles_if_necessary(config, tentacles_setup_config)
    else:
        # when no tentacles folder has been found
        logger.info("OctoBot tentacles can't be found. Installing default tentacles ...")
        commands.run_tentacles_install_or_update(config)
        config.load_profiles_if_possible_and_necessary()


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
        _log_environment(logger)

        # _check_public_announcements(logger)

        # load configuration
        config = _create_startup_config(logger)

        # check config loading
        if not config.is_loaded():
            raise errors.ConfigError

        # Handle utility methods before bot initializing if possible
        if args.encrypter:
            commands.exchange_keys_encrypter()
            return

        # add args to config
        update_config_with_args(args, config, logger)

        # show terms
        _log_terms_if_unaccepted(config, logger)

        # tries to load, install or repair tentacles
        _load_or_create_tentacles(config, logger)

        # Can now perform config health check (some checks require a loaded profile)
        configuration_manager.config_health_check(config, args.backtesting)

        # create OctoBot instance
        if args.backtesting:
            bot = octobot_backtesting.OctoBotBacktestingFactory(config,
                                                                run_on_common_part_only=not args.whole_data_range,
                                                                enable_join_timeout=args.enable_backtesting_timeout)
        else:
            bot = octobot_class.OctoBot(config, reset_trading_history=args.reset_trading_history)

        # set global bot instance
        octobot.set_bot(bot)

        # Clear community cache
        bot.community_auth.clear_cache()

        if args.identifier:
            # set community identifier
            bot.community_auth.identifier = args.identifier[0]

        if args.update:
            return commands.update_bot(bot.octobot_api)

        if args.strategy_optimizer:
            commands.start_strategy_optimizer(config, args.strategy_optimizer)
            return

        # In those cases load OctoBot
        _disable_interface_from_param("telegram", args.no_telegram, logger)
        _disable_interface_from_param("web", args.no_web, logger)

        commands.run_bot(bot, logger)

    except errors.ConfigError:
        logger.error("OctoBot can't start without a valid " + common_constants.CONFIG_FILE
                     + " configuration file." + "\nYou can use " +
                     constants.DEFAULT_CONFIG_FILE + " as an example to fix it.")
        os._exit(-1)

    except errors.NoProfileError:
        logger.error("OctoBot can't start without a valid default profile configuration.")
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
    parser.add_argument('-u', '--update', help='Update OctoBot to latest version.',
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
    parser.add_argument('-ebt', '--enable-backtesting-timeout',
                        help='When enabled, the watcher is limiting backtesting time to 30min.'
                             'When disabled, the backtesting run will not be interrupted during execution',
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
                                            "(ie the web interface that handle encryption automatically).",
                        action='store_true')
    parser.add_argument('--identifier', help="OctoBot community identifier.", type=str, nargs=1)
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


def start_background_octobot_with_args(version=False,
                                       update=False,
                                       encrypter=False,
                                       strategy_optimizer=False,
                                       data_collector=False,
                                       backtesting_files=None,
                                       no_telegram=False,
                                       no_web=False,
                                       backtesting=False,
                                       identifier=None,
                                       whole_data_range=True,
                                       enable_backtesting_timeout=True,
                                       simulate=True,
                                       risk=None,
                                       in_subprocess=False,
                                       reset_trading_history=False):
    if backtesting_files is None:
        backtesting_files = []
    args = argparse.Namespace(version=version,
                              update=update,
                              encrypter=encrypter,
                              strategy_optimizer=strategy_optimizer,
                              data_collector=data_collector,
                              backtesting_files=backtesting_files,
                              no_telegram=no_telegram,
                              no_web=no_web,
                              backtesting=backtesting,
                              identifier=identifier,
                              whole_data_range=whole_data_range,
                              enable_backtesting_timeout=enable_backtesting_timeout,
                              simulate=simulate,
                              risk=risk,
                              reset_trading_history=reset_trading_history)
    if in_subprocess:
        bot_process = multiprocessing.Process(target=start_octobot, args=(args,))
        bot_process.start()
        return bot_process
    else:
        return start_octobot(args)


def main(args=None):
    if not args:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(description='OctoBot')
    octobot_parser(parser)

    MIN_TENTACLE_MANAGER_VERSION = "1.0.10"

    # check compatible tentacle manager
    try:
        from octobot_tentacles_manager import VERSION

        if LooseVersion(VERSION) < MIN_TENTACLE_MANAGER_VERSION:
            print("OctoBot requires OctoBot-Tentacles-Manager in a minimum version of " + MIN_TENTACLE_MANAGER_VERSION +
                  " you can install and update OctoBot-Tentacles-Manager using the following command: "
                  "python3 -m pip install -U OctoBot-Tentacles-Manager", file=sys.stderr)
            sys.exit(-1)
    except ImportError:
        print("OctoBot requires OctoBot-Tentacles-Manager, you can install it using "
              "python3 -m pip install -U OctoBot-Tentacles-Manager", file=sys.stderr)
        sys.exit(-1)

    args = parser.parse_args(args)
    # call the appropriate command entry point
    args.func(args)
