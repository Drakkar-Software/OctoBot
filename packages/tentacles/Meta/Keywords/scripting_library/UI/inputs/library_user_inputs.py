#  Drakkar-Software OctoBot-Tentacles
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
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.configuration as commons_configuration
import tentacles.Meta.Keywords.scripting_library.TA.trigger.eval_triggered as eval_triggered
import octobot_tentacles_manager.api as tentacles_manager_api


def _find_configuration(nested_configuration, nested_config_names, element):
    for key, config in nested_configuration.items():
        if len(nested_config_names) == 0 and key == element:
            return config
        if isinstance(config, dict) and (len(nested_config_names) == 0 or key == nested_config_names[0]):
            found_config = _find_configuration(config, nested_config_names[1:], element)
            if found_config is not None:
                return found_config
    return None


async def external_user_input(
    ctx,
    name,
    tentacle,
    config_name=None,
    trigger_if_necessary=True,
    include_tentacle_as_requirement=True,
    config: dict = None
):
    triggered = False
    try:
        if config_name is None:
            query = await ctx.run_data_writer.search()
            raw_value = await ctx.run_data_writer.select(
                commons_enums.DBTables.INPUTS.value,
                (query.name == name) & (query.tentacle == tentacle)
            )
            if raw_value:
                return raw_value[0]["value"]
        else:
            # look for the user input in non nested user inputs
            user_inputs = await commons_configuration.get_user_inputs(ctx.run_data_writer)
            # First try with the current top level tentacle (faster and to avoid name conflicts)
            top_tentacle_config = ctx.top_level_tentacle.get_local_config()
            tentacle_config = _find_configuration(top_tentacle_config,
                                                  ctx.nested_config_names,
                                                  config_name.replace(" ", "_"))
            if tentacle_config is None:
                # Then try with the current local tentacle, then use all tentacles
                current_tentacle_config = ctx.tentacle.get_local_config()
                tentacle_config = current_tentacle_config.get(config_name.replace(" ", "_"), None)
            if tentacle_config is None:
                for local_user_input in user_inputs:
                    if not local_user_input["is_nested_config"] and \
                       local_user_input["input_type"] == commons_constants.NESTED_TENTACLE_CONFIG:
                        tentacle_config = _find_configuration(local_user_input["value"],
                                                              ctx.nested_config_names,
                                                              config_name.replace(" ", "_"))
                        if tentacle_config is not None:
                            break
                if not trigger_if_necessary:
                    # look into nested config as well since the tentacle wont be triggered
                    for local_user_input in user_inputs:
                        if local_user_input["is_nested_config"] and \
                                local_user_input["input_type"] == commons_constants.NESTED_TENTACLE_CONFIG:
                            if local_user_input["name"] == config_name:
                                tentacle_config = local_user_input["value"]
                                break
                            tentacle_config = _find_configuration(local_user_input["value"],
                                                                  ctx.nested_config_names,
                                                                  config_name.replace(" ", "_"))
                            if tentacle_config is not None:
                                break
            if tentacle_config is None and trigger_if_necessary:
                tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(tentacle) \
                    if isinstance(tentacle, str) else tentacle
                _, tentacle_config = await eval_triggered._trigger_single_evaluation(
                    ctx, tentacle_class,
                    commons_enums.CacheDatabaseColumns.VALUE.value,
                    None,
                    config_name, config)
                triggered = True
            try:
                return None if tentacle_config is None else tentacle_config[name.replace(" ", "_")]
            except KeyError:
                return None
    finally:
        if include_tentacle_as_requirement and not triggered and trigger_if_necessary:
            # to register the tentacle as requirement: trigger its evaluation in a nested context
            tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(tentacle) \
                if isinstance(tentacle, str) else tentacle
            await eval_triggered._trigger_single_evaluation(
                ctx, tentacle_class,
                commons_enums.CacheDatabaseColumns.VALUE.value,
                None,
                config_name, config)
    return None
