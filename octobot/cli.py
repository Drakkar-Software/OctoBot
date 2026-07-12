#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import argparse
import os
import pathlib
import sys
import multiprocessing
import asyncio
import traceback

import packaging.version as packaging_version

try:
    import octobot_commons.os_util as os_util
    import octobot_commons.logging
    import octobot_commons.configuration as configuration
    import octobot_commons.profiles as profiles
    import octobot_commons.authentication as authentication
    import octobot_commons.constants as common_constants
    import octobot_commons.errors as errors
    import octobot_commons.user_root_folder_provider as user_root_folder_provider

    import octobot_services.api as service_api

    import octobot_tentacles_manager.api as tentacles_manager_api
    import octobot_tentacles_manager.cli as tentacles_manager_cli
    import octobot_tentacles_manager.constants as tentacles_manager_constants
    import octobot_tentacles_manager

    import octobot_backtesting.constants as backtesting_constants

    # make tentacles importable
    sys.path.append(os.path.dirname(sys.executable))

    import octobot.octobot as octobot_class
    import octobot.octobot_node as octobot_node_class
    import octobot_node.config
    import octobot.commands as commands
    import octobot.configuration_manager as configuration_manager
    import octobot.octobot_backtesting_factory as octobot_backtesting
    import octobot.constants as constants
    import octobot.enums as enums
    import octobot.disclaimer as disclaimer
    import octobot.logger as octobot_logger
    import octobot.community as octobot_community
    import octobot.community.errors
    import octobot.limits as limits
except ImportError as err:
    traceback.print_exc()
    print(
        "Error importing OctoBot dependencies, please install OctoBot with the [full] option. "
        "Example: \"pip install -U octobot[full]\" "
        "(Error: {0}: {1})".format(err.__class__.__name__, str(err)), file=sys.stderr
    )
    sys.exit(-1)

def update_config_with_args(starting_args, config: configuration.Configuration, logger):
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


def _set_user_root_from_cli(user_folder: str) -> None:
    if not (user_folder and str(user_folder).strip()):
        raise errors.ConfigError("User folder must be a non-empty path.")
    if ".." in pathlib.PurePath(user_folder).parts:
        raise errors.ConfigError("Invalid user folder: parent directory segments are not allowed.")
    user_root_folder_provider.instance().set_root(os.path.normpath(user_folder))


def _log_environment(logger):
    try:
        bot_type = "cloud" if constants.IS_CLOUD_ENV else "self-hosted"
        logger.info(f"Running {bot_type} OctoBot on {os_util.get_current_platform()} "
                    f"with {os_util.get_octobot_type()} "
                    f"[Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}]")
    except Exception as e:
        logger.error(f"Impossible to identify the current running environment: {e}")


def _create_configuration():
    config_path = configuration.get_user_config()
    config = configuration.Configuration(
        config_path,
        user_root_folder_provider.get_user_profiles_folder(),
        constants.CONFIG_FILE_SCHEMA,
        constants.PROFILE_FILE_SCHEMA,
    )
    return config


def _create_startup_config(logger, default_config_file, *, is_process_child: bool = False):
    logger.info("Loading config files...")
    config = _create_configuration()
    is_first_startup = config.is_config_file_empty_or_missing()
    if is_first_startup:
        user_config_path = configuration.get_user_config()
        if is_process_child:
            raise errors.ConfigError(
                f"Process OctoBot child expected prepared {common_constants.CONFIG_FILE} at "
                f"{user_config_path!r} (under {common_constants.USER_AUTOMATIONS_FOLDER}/<automation_id>/). "
                f"The executor must materialize the automation layout before spawn; if this file is missing, "
                f"check ensure_user_profile_and_layout timing or parallel functional test races."
            )
        logger.info(
            f"No configuration found in {user_config_path}. "
            f"Creating default configuration..."
        )
        configuration_manager.init_config(
            config_file=user_config_path,
            from_config_file=default_config_file,
        )
        config.read(should_raise=False, activate_profile=False)
    else:
        _read_config(config, logger, activate_profile=False)
    distribution = configuration_manager.get_distribution(config.config)
    if distribution is not enums.OctoBotDistribution.DEFAULT:
        logger.info(f"Using {distribution.value} OctoBot distribution.")

    return config, is_first_startup


async def _apply_community_startup_info_to_config(logger, config, community_auth):
    try:
        startup_info = await community_auth.get_startup_info()
        logger.debug(f"Fetched startup info: {startup_info}")
        commands.download_and_select_profile(
            logger, config,
            startup_info.subscribed_products_urls,
            startup_info.forced_profile_url
        )
    except octobot_community.errors.BotError:
        return
    except authentication.FailedAuthentication as err:
        logger.error(f"Failed authentication when fetching bot startup info: {err}")
    except Exception as err:
        logger.error(f"Error when fetching community startup info: {err}")


async def _apply_db_bot_config(logger, config, community_auth) -> bool:
    try:
        # async loop may have changed if community_auth was already used before
        await community_auth.ensure_async_loop()
        profile_data, auth_data = await community_auth.fetch_bot_tentacles_data_based_config(
            constants.COMMUNITY_BOT_ID,
            constants.USER_AUTH_KEY,
        )
        profile = await config.profile_storage.import_profile_data(
            profile_data,
            constants.PROFILE_FILE_SCHEMA,
            None,
            name=profile_data.profile_details.name,
            auto_update=False,
            force_simulator=False,
        )
        for auth_data_element in auth_data:
            logger.info(f"Applying {auth_data_element.internal_name} exchange auth details")
            auth_data_element.apply_to_exchange_config(config)

        config.load_profiles()
    except octobot.community.errors.BotNotFoundError:
        raise errors.RemoteConfigError(
            f"COMMUNITY_BOT_ID env variable is required to apply bot config. "
            f"COMMUNITY_BOT_ID={constants.COMMUNITY_BOT_ID}"
        )
    except octobot.community.errors.MissingBotConfigError:
        raise
    except Exception as err:
        raise errors.RemoteConfigError(
            f"Error when fetching {constants.COMMUNITY_BOT_ID} bot configuration: {err} ({err.__class__.__name__})"
        )
    return commands.select_forced_profile_if_any(config, profile.profile_id, logger)


def _apply_env_variables_to_config(logger, config):
    commands.download_and_select_profile(
        logger, config,
        [url.strip() for url in constants.TO_DOWNLOAD_PROFILES.split(",")] if constants.TO_DOWNLOAD_PROFILES else [],
        constants.FORCED_PROFILE
    )


async def _get_authenticated_community_if_possible(config, logger):
    # switch environments if necessary
    octobot_community.IdentifiersProvider.use_environment_from_config(config)
    community_auth = octobot_community.CommunityAuthentication.create(config)
    community_auth.clear_local_data_if_necessary()
    try:
        if not community_auth.is_initialized():
            if constants.IS_CLOUD_ENV:
                authenticated = False
                try:
                    logger.debug("Attempting auth key authentication")
                    authenticated = await community_auth.auto_reauthenticate()
                except authentication.AuthenticationError as err:
                    logger.info(f"Auth key auth failure ({err}). Trying other methods if available.")
                if not authenticated and constants.USER_ACCOUNT_EMAIL and constants.USER_PASSWORD_TOKEN:
                    try:
                        logger.debug("Attempting password token authentication")
                        await community_auth.login(
                            constants.USER_ACCOUNT_EMAIL, None, password_token=constants.USER_PASSWORD_TOKEN
                        )
                    except authentication.AuthenticationError as err:
                        logger.info(f"Password token auth failure ({err}). Trying with saved session.")
            if not community_auth.is_initialized():
                # try with saved credentials if any
                has_tentacles = tentacles_manager_api.is_tentacles_architecture_valid()
                # When no tentacles or in cloud, fetch private data. Otherwise fetch it later on in bot init
                fetch_private_data = not has_tentacles or constants.IS_CLOUD_ENV
                await community_auth.async_init_account(fetch_private_data=fetch_private_data)
        if not community_auth.is_logged_in():
            logger.info("No authenticated community account")
    except authentication.FailedAuthentication as err:
        logger.error(f"Failed authentication when initializing community authenticator: {err}")
    except Exception as err:
        logger.error(f"Error when initializing community authenticator: {err}")
    return community_auth


async def _async_load_community_data(community_auth, config, logger, is_first_startup):
    if constants.IS_CLOUD_ENV:
        if is_first_startup:
            if not community_auth.is_logged_in():
                raise authentication.FailedAuthentication(
                    "Impossible to load community data without an authenticated user account"
                )
            # auto config
            if constants.USE_FETCHED_BOT_CONFIG:
                await _apply_db_bot_config(logger, config, community_auth)
            else:
                await _apply_community_startup_info_to_config(logger, config, community_auth)
        await community_auth.community_bot.on_started_bot()


def _apply_forced_configs(community_auth, logger, config, is_first_startup):
    asyncio.run(_async_load_community_data(community_auth, config, logger, is_first_startup))

    # 2. handle profiles from env variables
    _apply_env_variables_to_config(logger, config)


def _read_config(config, logger, *, activate_profile=True):
    try:
        config.read(
            should_raise=True,
            fill_missing_fields=True,
            activate_profile=activate_profile,
        )
    except errors.NoProfileError:
        _repair_with_default_profile(config, logger)
        config = _create_configuration()
        config.read(
            should_raise=False,
            fill_missing_fields=True,
            activate_profile=activate_profile,
        )
    except Exception as e:
        raise errors.ConfigError(e)


def _activate_saved_profile_after_sync(config, logger):
    config.activate_saved_profile()
    commands.ensure_profile(config)
    _validate_config(config, logger)


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


def _load_or_create_tentacles(community_auth, config, logger, *, is_process_child: bool = False):
    # add tentacles folder to Python path
    sys.path.append(os.path.realpath(os.getcwd()))

    # Process children store readonly_reference_tentacles_path in config.json and have no
    # local reference_tentacles_config/. Apply the override before probing whether the
    # reference config file exists, so the path resolves to the master tree.
    config.apply_readonly_reference_tentacles_override()

    if os.path.isfile(
        user_root_folder_provider.get_user_reference_tentacle_config_file_path()
    ):
        # when tentacles folder already exists
        config.load_profiles_if_possible_and_necessary()
        tentacles_setup_config = config.get_active_tentacles_setup_config()
        if (
            is_process_child
            and config.config.get(common_constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH)
        ):
            # Process children share the master reference tree; skip repair that would write to it.
            if not tentacles_manager_api.load_tentacles(verbose=True):
                logger.error("OctoBot tentacles failed to load for process child.")
            config.save(schema_file=config.config_schema_path)
        else:
            commands.run_update_or_repair_tentacles_if_necessary(
                community_auth, config, tentacles_setup_config
            )
    else:
        # when no tentacles folder has been found
        logger.info("OctoBot tentacles can't be found. Installing default tentacles ...")
        commands.run_tentacles_install_or_update(community_auth, config)
        config.load_profiles_if_possible_and_necessary()


def _init_cli_overriden_folders(args):
    overrides = {}
    if args.user_folder:
        overrides["user_folder"] = args.user_folder
        _set_user_root_from_cli(args.user_folder)
    if args.log_folder:
        overrides["log_folder"] = args.log_folder
        logs_folder = args.log_folder
    else:
        logs_folder = constants.LOGS_FOLDER
    return overrides, logs_folder


def _assert_process_child_folder_overrides(args) -> None:
    """When ``--dump-state`` is set (DSL process children), require an automation-scoped ``--user-folder``."""
    if not args.dump_state or not str(args.dump_state).strip():
        return
    user_folder = args.user_folder
    if not user_folder or not str(user_folder).strip():
        raise errors.ConfigError(
            "Process OctoBot children require --user-folder under "
            f"{common_constants.USER_AUTOMATIONS_FOLDER}/<automation_id>/ when --dump-state is set."
        )
    path_segments = tuple(
        segment
        for segment in str(user_folder).replace("\\", "/").split("/")
        if segment
    )
    expected_prefix = (
        common_constants.USER_FOLDER,
        common_constants.AUTOMATIONS_FOLDER,
    )
    if len(path_segments) < len(expected_prefix) + 1:
        raise errors.ConfigError(
            "Process OctoBot children require --user-folder under "
            f"{common_constants.USER_AUTOMATIONS_FOLDER}/<automation_id>/, got "
            f"{user_folder!r}."
        )
    if path_segments[: len(expected_prefix)] != expected_prefix:
        raise errors.ConfigError(
            "Process OctoBot children require --user-folder to start with "
            f"{common_constants.USER_AUTOMATIONS_FOLDER}/, got {user_folder!r}."
        )
    if ".." in path_segments:
        raise errors.ConfigError(
            f"Invalid --user-folder for process child: parent segments are not allowed ({user_folder!r})."
        )

def _configure_profile_sync_user(config, community_auth, *, is_process_child: bool = False):
    if is_process_child:
        sync_user_id = constants.PROCESS_BOT_SYNC_USER_ID
        if not sync_user_id:
            raise errors.ConfigError(
                "Process OctoBot children require "
                f"{constants.ENV_PROCESS_BOT_SYNC_USER_ID} to be set by the executor."
            )
        config.profile_storage.bind_process_child_sync_user_id(sync_user_id)
        return
    if community_auth is not None and community_auth.auto_init_sync_client():
        config.profile_storage.configure_sync_user(community_auth.sync_user_id)


def _apply_node_cli_settings(args) -> None:
    if args.master:
        octobot_node.config.settings.IS_MASTER_MODE = True
    octobot_node.config.settings.CONSUMER_ONLY = args.consumer_only


def _apply_node_startup_settings(args) -> None:
    constants.FORCED_DISTRIBUTION = enums.OctoBotDistribution.NODE.value
    args.no_web = True


def _apply_trading_startup_settings() -> None:
    constants.FORCED_DISTRIBUTION = enums.OctoBotDistribution.DEFAULT.value


def _apply_startup_distribution_mode(args) -> None:
    _apply_node_cli_settings(args)
    if args.trading or args.backtesting:
        _apply_trading_startup_settings()
    else:
        _apply_node_startup_settings(args)


def _log_startup_distribution_mode(logger, args) -> None:
    if args.backtesting:
        startup_message = "Starting OctoBot in backtesting mode."
    elif args.trading:
        startup_message = (
            "Starting OctoBot in trading mode: will trade using the selected profile."
        )
    else:
        startup_message = (
            "Starting OctoBot in node mode: use the interface to start OctoBots that trade "
            "from your selected strategy on the exchanges of your choice."
        )
    if not args.backtesting:
        if args.master:
            startup_message += " Master scheduler enabled."
        if args.consumer_only:
            startup_message += " Consumer-only worker mode enabled."
    logger.info(startup_message)


def start_octobot(args, default_config_file=None):
    logger = None
    try:
        if args.version:
            print(constants.LONG_VERSION)
            return
        
        overrides, logs_folder = _init_cli_overriden_folders(args)
        _assert_process_child_folder_overrides(args)
        logger = octobot_logger.init_logger(logs_folder=logs_folder)
        _apply_startup_distribution_mode(args)
        _log_startup_distribution_mode(logger, args)
        startup_messages = []

        # Version
        logger.info("Version : {0}".format(constants.LONG_VERSION))

        # Log folder overrides
        if overrides:
            logger.info(f"Overriding default folders: {overrides}")
        else:
            logger.info(f"Using default folders")

        # Current running environment
        _log_environment(logger)

        octobot_community.init_sentry_tracker()

        # load configuration
        is_process_child = bool(args.dump_state and str(args.dump_state).strip())
        config, is_first_startup = _create_startup_config(
            logger,
            default_config_file or constants.DEFAULT_CONFIG_FILE,
            is_process_child=is_process_child,
        )

        # check config loading
        if not config.is_loaded():
            raise errors.ConfigError

        # Handle utility methods before bot initializing if possible
        if args.encrypter:
            commands.exchange_keys_encrypter()
            return

        # show terms
        _log_terms_if_unaccepted(config, logger)

        community_auth = None if args.backtesting else asyncio.run(
            _get_authenticated_community_if_possible(config, logger)
        )

        _configure_profile_sync_user(
            config,
            community_auth,
            is_process_child=is_process_child,
        )

        _activate_saved_profile_after_sync(config, logger)

        # tries to load, install or repair tentacles
        _load_or_create_tentacles(community_auth, config, logger, is_process_child=is_process_child)

        # patch setup with forced values
        if not args.backtesting:
            _apply_forced_configs(community_auth, logger, config, is_first_startup)

        # apply CLI overrides after profile activation (trader keys come from profile)
        update_config_with_args(args, config, logger)

        # Can now perform config health check (some checks require a loaded profile)
        configuration_manager.config_health_check(config, args.backtesting)

        # Apply config limits if any
        startup_messages += limits.apply_config_limits(config)

        # create OctoBot instance
        distribution = configuration_manager.get_distribution(config.config)
        if args.backtesting:
            bot = octobot_backtesting.OctoBotBacktestingFactory(config,
                                                                run_on_common_part_only=not args.whole_data_range,
                                                                enable_join_timeout=args.enable_backtesting_timeout,
                                                                enable_logs=not args.no_logs)
        elif distribution is enums.OctoBotDistribution.NODE:
            bot = octobot_node_class.OctoBotNode(config, community_authenticator=community_auth,
                                        reset_trading_history=args.reset_trading_history,
                                        startup_messages=startup_messages)
        else:
            bot = octobot_class.OctoBot(config, community_authenticator=community_auth,
                                        reset_trading_history=args.reset_trading_history,
                                        startup_messages=startup_messages)

        if not args.backtesting:
            path = args.dump_state
            if path:
                bot.dump_state_path = os.path.normpath(path)

        # set global bot instance
        commands.set_global_bot_instance(bot)

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
        force_error_exit = False
    except errors.RemoteConfigError as err:
        logger.exception(err)
        force_error_exit = True

    except errors.ConfigError as err:
        logger.error("OctoBot can't start without a valid " + common_constants.CONFIG_FILE
                     + " configuration file.\nError: " + str(err) + "\nYou can use " +
                     constants.DEFAULT_CONFIG_FILE + " as an example to fix it.")
        force_error_exit = True

    except errors.NoProfileError:
        logger.error("Missing default profiles. OctoBot can't start without a valid default profile configuration. "
                     "Please make sure that the {config.profiles_path} "
                     f"folder is accessible. To reinstall default profiles, delete the "
                     f"'{tentacles_manager_constants.TENTACLES_PATH}' "
                     f"folder or start OctoBot with the following arguments: tentacles --install --all")
        force_error_exit = True

    except ModuleNotFoundError as err:
        if 'tentacles' in str(err):
            logger.error("Impossible to start OctoBot, tentacles are missing.\nTo install tentacles, "
                         "please use the following command:\nstart.py tentacles --install --all")
        else:
            logger.exception(err)
        force_error_exit = True

    except errors.ConfigEvaluatorError:
        logger.error("OctoBot can't start without a valid  configuration file.\n"
                     "This file is generated on tentacle "
                     "installation using the following command:\nstart.py tentacles --install --all")
        force_error_exit = True

    except errors.ConfigTradingError:
        logger.error("OctoBot can't start without a valid configuration file.\n"
                     "This file is generated on tentacle "
                     "installation using the following command:\nstart.py tentacles --install --all")
        force_error_exit = True
    if force_error_exit:
        octobot_community.flush_tracker()
        os._exit(-1)


def octobot_parser(parser, default_config_file=None):
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
    parser.add_argument(
        '--user-folder',
        type=str,
        default=None,
        help='User data root (config, profiles, reference tentacles). Relative to the current working directory.',
    )
    parser.add_argument(
        '--log-folder',
        type=str,
        default=None,
        help='Log files directory. When set, overrides the LOGS_FOLDER environment variable and default "logs".',
    )
    parser.add_argument('-nw', '--no_web', help="Don't start OctoBot web interface.",
                        action='store_true')
    parser.add_argument('-nl', '--no_logs', help="Disable OctoBot logs in backtesting.",
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
    parser.add_argument(
        "--dump-state",
        type=str,
        default=None,
        help="Absolute path of the JSON file where OctoBot periodically writes ProcessBotState (liveness, "
        "next to the user config directory). Omitted in normal use; spawned DSL children pass this explicitly.",
    )
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
    parser.add_argument(
        '--trading',
        help='Start classic trading OctoBot with the trading web interface (default startup is node mode).',
        action='store_true',
    )
    _register_node_arguments(parser)
    parser.set_defaults(func= lambda args: start_octobot(args, default_config_file))

    # add sub commands
    subparsers = parser.add_subparsers(title="Other commands")

    # tentacles manager
    tentacles_parser = subparsers.add_parser("tentacles", help='Calls OctoBot tentacles manager.\n'
                                                               'Use "tentacles --help" to get the '
                                                               'tentacles manager help.')
    tentacles_manager_cli.register_tentacles_manager_arguments(tentacles_parser)
    tentacles_parser.set_defaults(func=commands.call_tentacles_manager)

def _register_node_arguments(parser):
    parser.add_argument(
        '--host',
        help='Host to bind the server to.',
        type=str,
        default=None
    )
    parser.add_argument(
        '--port',
        help='Port to bind the server to (default: 8000).',
        type=int,
        default=None
    )
    parser.add_argument(
        '--master',
        help='Enable master node mode (schedules and executes tasks, UI enabled by default).',
        action='store_true'
    )
    parser.add_argument(
        '--consumer_only',
        help='Start OctoBot Node in consumer only mode, in case the master node is not enough (requires a postgres database).',
        type=bool,
        default=False
    )


def start_background_octobot_with_args(
    version=False,
    update=False,
    encrypter=False,
    strategy_optimizer=False,
    data_collector=False,
    backtesting_files=None,
    no_telegram=False,
    no_web=False,
    no_logs=False,
    backtesting=False,
    identifier=None,
    whole_data_range=True,
    enable_backtesting_timeout=True,
    simulate=True,
    risk=None,
    in_subprocess=False,
    reset_trading_history=False,
    default_config_file=None,
    user_folder=None,
    log_folder=None,
    trading=True,
    master=False,
    consumer_only=False,
    host=None,
    port=None,
):
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
                              no_logs=no_logs,
                              backtesting=backtesting,
                              identifier=identifier,
                              whole_data_range=whole_data_range,
                              enable_backtesting_timeout=enable_backtesting_timeout,
                              simulate=simulate,
                              risk=risk,
                              reset_trading_history=reset_trading_history,
                              user_folder=user_folder,
                              log_folder=log_folder,
                              trading=trading,
                              master=master,
                              consumer_only=consumer_only,
                              host=host,
                              port=port,
                              dump_state=None)
    if in_subprocess:
        bot_process = multiprocessing.Process(target=start_octobot, args=(args, default_config_file))
        bot_process.start()
        return bot_process
    else:
        return start_octobot(args, default_config_file)


def main(args=None, default_config_file=None):
    if not args:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(description='OctoBot')
    octobot_parser(parser, default_config_file=default_config_file)

    MIN_TENTACLE_MANAGER_VERSION = "1.0.10"

    # check compatible tentacle manager
    try:
        if packaging_version.Version(octobot_tentacles_manager.VERSION) < packaging_version.Version(MIN_TENTACLE_MANAGER_VERSION):
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
