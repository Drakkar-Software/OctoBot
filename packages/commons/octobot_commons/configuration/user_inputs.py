# pylint: disable=W1203,R0902,R0913,R0914
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
import contextlib

import octobot_commons.enums as enums
import octobot_commons.dict_util as dict_util


class UserInput:
    MAX_ORDER = 9999

    def __init__(
        self,
        name,
        input_type,
        value,
        def_val,
        tentacle_type,
        tentacle_name,
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
    ):
        self.name = name
        self.input_type = input_type
        self.value = value
        self.def_val = def_val
        self.tentacle_type = tentacle_type
        self.tentacle_name = tentacle_name
        self.min_val = min_val
        self.max_val = max_val
        self.options = options
        self.title = title
        self.item_title = item_title
        self.other_schema_values = other_schema_values
        self.editor_options = editor_options
        self.read_only = read_only
        self.is_nested_config = is_nested_config
        self.nested_tentacle = nested_tentacle
        self.parent_input_name = parent_input_name
        self.show_in_summary = show_in_summary
        self.show_in_optimizer = show_in_optimizer
        self.path = path
        self.order = order

    def to_dict(self):
        """
        :return: the dict representation of the UserInput
        """
        return {
            "name": self.name,
            "input_type": (
                self.input_type
                if isinstance(self.input_type, str)
                else self.input_type.value
            ),
            "value": self.value,
            "def_val": self.def_val,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "options": self.options,
            "title": self.title,
            "item_title": self.item_title,
            "other_schema_values": self.other_schema_values,
            "editor_options": self.editor_options,
            "read_only": self.read_only,
            "tentacle_type": self.tentacle_type,
            "tentacle": self.tentacle_name,
            "nested_tentacle": self.nested_tentacle,
            "parent_input_name": self.parent_input_name,
            "is_nested_config": self.is_nested_config,
            "in_summary": self.show_in_summary,
            "in_optimizer": self.show_in_optimizer,
            "path": self.path,
            "order": self.order,
        }


class UserInputFactory:
    def __init__(self, user_input_tentacle_type: enums.UserInputTentacleTypes):
        self.user_input_tentacle_type: enums.UserInputTentacleTypes = (
            user_input_tentacle_type
        )
        self.tentacle_class = None
        self.tentacle_config_proxy = None

    def set_tentacle_class(self, tentacle_class):
        """
        set the associated tentacle class
        :return: self
        """
        self.tentacle_class = tentacle_class
        return self

    def set_tentacle_config_proxy(self, tentacle_config_proxy):
        """
        set the associated tentacle configuration proxy function
        :return: self
        """
        self.tentacle_config_proxy = tentacle_config_proxy
        return self

    def user_input(
        self,
        name: str,
        input_type,
        def_val,
        registered_inputs: dict,
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
        return_value_only=True,
        update_parent_value=True,
    ):
        """
        Set and return a user input value.
        The returned value is set as an attribute named as the "name" param with " " replaced by "_"
        in self.specific_config.
        Types are any UserInputTypes
        :return: the saved_config value if any, def_val otherwise
        """
        sanitized_name = sanitize_user_input_name(name)
        parent = _find_parent_config_node(
            self.tentacle_config_proxy(), parent_input_name, array_indexes
        )
        used_value = value
        if value is None:
            # value is not provided, use def_val
            used_value = def_val
            if parent is not None:
                # parent found, try to find saved value
                try:
                    used_value = parent[sanitized_name]
                except KeyError:
                    # use default value
                    pass
        input_key = f"{parent_input_name}{name}"
        created_input = UserInput(
            name,
            input_type,
            used_value,
            def_val,
            self.user_input_tentacle_type.value,
            self.tentacle_class.get_name(),
            min_val=min_val,
            max_val=max_val,
            options=options,
            title=title,
            item_title=item_title,
            other_schema_values=other_schema_values,
            editor_options=editor_options,
            read_only=read_only,
            is_nested_config=is_nested_config,
            nested_tentacle=nested_tentacle,
            parent_input_name=parent_input_name,
            show_in_summary=show_in_summary,
            show_in_optimizer=show_in_optimizer,
            path=path,
            order=order,
        )
        if input_key not in registered_inputs:
            # do not register user input multiple times
            registered_inputs[input_key] = created_input
        if parent is not None and update_parent_value:
            parent[sanitized_name] = used_value
        return used_value if return_value_only else created_input

    @contextlib.contextmanager
    def local_factory(self, tentacle_class, tentacle_config_proxy):
        """
        temporarily set the associated tentacle class and tentacle config proxy
        """
        previous_tentacle_class = self.tentacle_class
        previous_tentacle_config_proxy = self.tentacle_config_proxy
        try:
            self.set_tentacle_class(tentacle_class).set_tentacle_config_proxy(
                tentacle_config_proxy
            )
            yield
        finally:
            self.set_tentacle_class(previous_tentacle_class).set_tentacle_config_proxy(
                previous_tentacle_config_proxy
            )


def sanitize_user_input_name(name):
    """
    :return: the sanitized user input name
    """
    return name.replace(" ", "_")


async def save_user_input(
    u_input: UserInput,
    run_data_writer,
    flush_if_necessary=False,
    skip_flush=False,
):
    """
    Save the user input in the given run_data_writer. First checks if the user input is not already present.
    Does not update a user input if it is already saved in run_data_writer.
    """
    if not run_data_writer.enable_storage:
        return
    if not await run_data_writer.contains_row(
        enums.DBTables.INPUTS.value,
        {
            "name": u_input.name,
            "tentacle": u_input.tentacle_name,
            "nested_tentacle": u_input.nested_tentacle,
            "parent_input_name": u_input.parent_input_name,
            "is_nested_config": u_input.is_nested_config,
        },
    ):
        await run_data_writer.log(
            enums.DBTables.INPUTS.value,
            u_input.to_dict(),
        )
        if not skip_flush and (
            flush_if_necessary or run_data_writer.are_data_initialized
        ):
            # in some cases, user inputs might be setup after the 1st trading mode cycle: flush
            # writer in live mode to ensure writing
            await run_data_writer.flush()


def get_user_input_tentacle_type(tentacle) -> str:
    """
    :return: the tentacle associated UserInputTentacleTypes
    """
    return (
        enums.UserInputTentacleTypes.TRADING_MODE.value
        if hasattr(tentacle, "trading_config")
        else (
            enums.UserInputTentacleTypes.EVALUATOR.value
            if hasattr(tentacle, "specific_config")
            else enums.UserInputTentacleTypes.EXCHANGE.value
        )
    )


async def get_user_inputs(reader, tentacle_name=None):
    """
    :return: all user inputs. Only user inputs associated to the given tentacle_name that have been saved into
    the given reader if tentacle_name is given
    """
    all_inputs = await reader.all(enums.DBTables.INPUTS.value)
    if tentacle_name is None:
        return all_inputs
    return [
        selected_input
        for selected_input in all_inputs
        if selected_input["tentacle"] == tentacle_name
    ]


async def clear_user_inputs(writer, tentacle_name=None):
    """
    Delete all user inputs. Only delete user inputs associated to tentacle_name if tentacle_name is given
    """
    if tentacle_name is None:
        await writer.delete_all(enums.DBTables.INPUTS.value)
    else:
        query = {"tentacle": tentacle_name}
        await writer.delete(enums.DBTables.INPUTS.value, query)


def _find_parent_config_node(tentacle_config, parent_input_name, array_indexes):
    """
    :return: the found parent node from tentacles_config
    """
    if parent_input_name is not None:
        found, nested_parent = dict_util.find_nested_value(
            tentacle_config,
            sanitize_user_input_name(parent_input_name),
            list_indexes=array_indexes,
        )
        if found and isinstance(nested_parent, dict):
            return nested_parent
        if found and isinstance(nested_parent, list) and array_indexes:
            return nested_parent[array_indexes[-1]]
        # non dict or list with array_indexes nested parents are not supported
        return None
    return tentacle_config
