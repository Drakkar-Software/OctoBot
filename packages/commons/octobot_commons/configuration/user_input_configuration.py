# pylint: disable=W0718
#  Drakkar-Software OctoBot-Commons
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

import octobot_commons.logging as logging
import octobot_commons.configuration.user_inputs as user_inputs
import octobot_commons.databases.run_databases.run_databases_provider as run_databases_provider

try:
    import octobot_tentacles_manager.api
except ImportError:
    pass


def load_user_inputs_from_class(
    configured_class, tentacles_setup_config, to_fill_config
) -> dict:
    """
    Apply the given tentacles_setup_config configuration to the given to_fill_config using configured_class user inputs
    Requires octobot_tentacles_manager import, configured_class.CLASS_UI, configured_class.init_user_inputs
    and configured_class.get_name
    :return: the filled user input configuration
    """
    inputs = {}
    try:
        to_fill_config.update(
            octobot_tentacles_manager.api.get_tentacle_config(
                tentacles_setup_config, configured_class
            )
        )
    except NotImplementedError:
        # get_name not implemented, no tentacle config
        return inputs
    logger = logging.get_logger(configured_class.get_name())
    try:
        with configured_class.CLASS_UI.local_factory(
            configured_class, lambda: to_fill_config
        ):
            configured_class.init_user_inputs_from_class(inputs)
    except Exception as err:
        logger.exception(err, True, f"Error when initializing user inputs: {err}")
    if to_fill_config:
        logger.debug(f"Using config: {to_fill_config}")
    return inputs


async def load_and_save_user_inputs(tentacle_instance, bot_id: str) -> dict:
    """
    Requires an instance of the tentacle and the init_user_inputs method
    Initialize and save the user inputs of the tentacle in run data
    :return: the filled user input configuration
    """
    inputs = {}
    try:
        tentacle_instance.init_user_inputs(inputs)
        if run_databases_provider.RunDatabasesProvider.instance().is_storage_enabled(
            bot_id
        ):
            run_db = run_databases_provider.RunDatabasesProvider.instance().get_run_db(
                bot_id
            )
            await user_inputs.clear_user_inputs(run_db, tentacle_instance.get_name())
            for user_input in inputs.values():
                await user_inputs.save_user_input(user_input, run_db)
            await run_db.flush()
    except Exception as err:
        tentacle_instance.logger.exception(
            err, True, f"Error when initializing user inputs: {err}"
        )
    return inputs


def get_raw_config_and_user_inputs_from_class(
    configured_class, tentacles_setup_config
) -> (dict, list):
    """
    Requires octobot_tentacles_manager import and configured_class.load_user_inputs
    :return: the filled user input configuration of configured_class according to the given tentacles_setup_config
    """
    loaded_config = octobot_tentacles_manager.api.get_tentacle_config(
        tentacles_setup_config, configured_class
    )
    created_user_inputs = configured_class.load_user_inputs_from_class(
        tentacles_setup_config, loaded_config
    )
    return loaded_config, list(
        user_input.to_dict() for user_input in created_user_inputs.values()
    )


async def get_raw_config_and_user_inputs(
    configured_class, config, tentacles_setup_config, bot_id
) -> (dict, list):
    """
    Requires octobot_tentacles_manager import and configured_class.create_local_instance
    Uses run data to load user input values when available
    :return: the tentacle configuration and its list of user inputs
    """
    loaded_config = octobot_tentacles_manager.api.get_tentacle_config(
        tentacles_setup_config, configured_class
    )
    if saved_user_inputs := await user_inputs.get_user_inputs(
        run_databases_provider.RunDatabasesProvider.instance().get_run_db(bot_id),
        configured_class.get_name(),
    ):
        # user inputs have been saved in run database, use those as they might contain additional
        # (nested) user inputs
        return loaded_config, saved_user_inputs
    # use user inputs from init_user_inputs
    tentacle_instance = configured_class.create_local_instance(
        config, tentacles_setup_config, loaded_config
    )
    created_user_inputs = {}
    tentacle_instance.init_user_inputs(created_user_inputs)
    return loaded_config, list(
        user_input.to_dict() for user_input in created_user_inputs.values()
    )
