#  Drakkar-Software OctoBot-Trading
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
import octobot_commons.configuration as configuration


async def user_input(
    ctx,
    name,
    input_type,
    def_val,
    value=None,
    min_val=None,
    max_val=None,
    options=None,
    title=None,
    item_title=None,
    other_schema_values=None,
    editor_options=None,
    read_only=False,
    is_nested_config=None,
    nested_tentacle=None,
    parent_input_name=None,
    show_in_summary=True,
    show_in_optimizer=True,
    path=None,
    order=None,
    array_indexes=None,
    flush_if_necessary=False,
    should_save_user_input=True,
):
    """
    Set and return a user input value.
    Types are: int, float, boolean, options, multiple-options, text
    :return:
    """
    created_input = _get_user_input_factory(ctx).user_input(
        name,
        input_type,
        def_val,
        {},
        value=value,
        min_val=min_val,
        max_val=max_val,
        options=options,
        title=title,
        item_title=item_title,
        other_schema_values=other_schema_values,
        editor_options=editor_options,
        read_only=read_only,
        is_nested_config=ctx.is_nested_tentacle if is_nested_config is None else is_nested_config,
        nested_tentacle=nested_tentacle,
        parent_input_name=parent_input_name,
        show_in_summary=show_in_summary,
        show_in_optimizer=show_in_optimizer,
        path=path,
        order=order,
        array_indexes=array_indexes,
        return_value_only=False,
        update_parent_value=should_save_user_input,
    )
    if should_save_user_input and ctx.run_data_writer is not None:
        await configuration.save_user_input(
            created_input,
            ctx.run_data_writer,
            flush_if_necessary=flush_if_necessary,
            skip_flush=ctx.exchange_manager.is_backtesting,
        )
    return created_input.value


async def save_user_input(
    ctx,
    name,
    input_type,
    value,
    def_val,
    min_val=None,
    max_val=None,
    options=None,
    title=None,
    item_title=None,
    other_schema_values=None,
    editor_options=None,
    read_only=False,
    is_nested_config=None,
    nested_tentacle=None,
    parent_input_name=None,
    show_in_summary=True,
    show_in_optimizer=True,
    path=None,
    order=None,
    array_indexes=None,
    flush_if_necessary=False
):
    await configuration.save_user_input(
        _get_user_input_factory(ctx).user_input(
            name,
            input_type,
            def_val,
            {},
            value=value,
            min_val=min_val,
            max_val=max_val,
            options=options,
            title=title,
            item_title=item_title,
            other_schema_values=other_schema_values,
            editor_options=editor_options,
            read_only=read_only,
            is_nested_config=ctx.is_nested_tentacle if is_nested_config is None else is_nested_config,
            nested_tentacle=nested_tentacle,
            parent_input_name=parent_input_name,
            show_in_summary=show_in_summary,
            show_in_optimizer=show_in_optimizer,
            path=path,
            order=order,
            array_indexes=array_indexes,
            return_value_only=False,
        ),
        ctx.run_data_writer,
        flush_if_necessary=flush_if_necessary,
        skip_flush=ctx.exchange_manager.is_backtesting,
    )


async def get_activation_topics(context, default_value, options):
    return await user_input(
        context, commons_constants.CONFIG_ACTIVATION_TOPICS, commons_enums.UserInputTypes.OPTIONS.value,
        default_value,
        options=options,
        show_in_optimizer=False, show_in_summary=False, order=1000
    )


def _get_user_input_factory(context):
    factory = configuration.UserInputFactory(context.tentacle.USER_INPUT_TENTACLE_TYPE)
    factory.set_tentacle_class(context.tentacle).set_tentacle_config_proxy(context.tentacle.get_local_config)
    return factory
